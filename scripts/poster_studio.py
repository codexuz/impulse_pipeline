"""
Poster Studio — Figma posters on Google Flow artwork, driven by one poster spec.

Roles:
  Google Flow  only the text-free artwork (scene, hero object, light) and photo edits.
  Figma        the poster itself: logo, every text, icons, chips, contacts as editable layers, Feed + Story frames.
  Spec         workspace/05_posters/drafts/<poster_id>.json — texts, layers, styles, art prompt, Figma node ids.

Where the design comes from (spec.mode):
  reference  the user's reference poster is copied with 100% parity: Claude measures it on the grid
             (poster_reference.py) and writes the layers 1:1; Flow redraws its scene from a clean plate
             (texts inpainted out) with the user's own assets. Only the content (texts, logo, contacts, assets)
             is the user's. Later change requests are applied on top and logged in parity.deviations.
  wishes     no reference: layout from the poster type template (assets/poster_templates/<type>.json) or
             another poster (--from), artwork prompt from the user's wishes.

Flow:
  1. new      python scripts/poster_studio.py new --id olimpiada_2027 --type announcement --reference ref.jpg --texts t.json
              (reference: then read refs/<id>/reference_grid.png + `measure`, write layers/styles/art/parity.text_boxes)
  2. art      python scripts/poster_studio.py art --id <id>      -> Flow request; flow_generate -> flow_wait ->
              python scripts/flow_assets.py import workspace/flow_requests/<id>_art.json
  3. upload   python scripts/poster_studio.py upload --id <id>   -> N images; upload_assets(fileKey, count=N) ->
              python scripts/poster_studio.py upload --id <id> --url <submitUrl> --url ...
  4. figma    python scripts/poster_studio.py figma --id <id>    -> workspace/05_posters/figma/<id>.js -> use_figma(code)
              save the returned JSON: python scripts/poster_studio.py record --id <id> --result result.json
  5. export   download_assets(nodeId) per frame -> python scripts/poster_studio.py export --id <id> --url feed=<url> --url story=<url>
  6. verify   python scripts/poster_studio.py verify --id <id>   -> text check sheet (+ parity sheet in reference mode)
  Edit:       python scripts/poster_studio.py edit --id <id> --set date="2-noyabr, 2026-yil"      (texts -> figma --texts)
              python scripts/poster_studio.py edit --id <id> --layer title.size=96 --layer story:logo.y=260 --change "bigger title"
              python scripts/poster_studio.py art --id <id> --change "make the light ribbons brighter"
"""
import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flow_assets import _write_request, rel, resolve  # noqa: E402
from flow_design import BRAND, COLORS, FORMATS, art_scenes  # noqa: E402
import poster_reference  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = ROOT / "workspace/05_posters/drafts"
FINAL_DIR = ROOT / "workspace/05_posters/final"
REFS_DIR = ROOT / "workspace/05_posters/refs"
FIGMA_DIR = ROOT / "workspace/05_posters/figma"
TEMPLATES_DIR = ROOT / "assets/poster_templates"
RENDERER = ROOT / "scripts/figma/render_poster.js"
ICONS_DIR = ROOT / "scripts/figma/node_modules"
IMAGE_CACHE = FIGMA_DIR / "image_cache.json"
for d in (DRAFTS_DIR, FINAL_DIR, REFS_DIR, FIGMA_DIR):
    d.mkdir(parents=True, exist_ok=True)

FIGMA = BRAND["figma"]
POSTER_SETTINGS = BRAND["poster_settings"]
HEADING_FONT = BRAND["typography"]["heading"]


# ---------------------------------------------------------------------------
# Spec storage
# ---------------------------------------------------------------------------

def spec_path(poster_id: str) -> Path:
    return DRAFTS_DIR / f"{poster_id}.json"


def load_spec(poster_id: str) -> dict:
    path = spec_path(poster_id)
    if not path.exists():
        raise SystemExit(f"Poster spec topilmadi: {rel(path)} (avval `new`)")
    return json.loads(path.read_text(encoding="utf-8"))


def save_spec(spec: dict, note: str | None = None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    spec["updated_at"] = now
    if note:
        spec.setdefault("history", []).append({"at": now, "note": note})
    spec_path(spec["poster_id"]).write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")


def output_path(poster_id: str, fmt: str) -> Path:
    return FINAL_DIR / f"{poster_id}_{FORMATS[fmt]['suffix']}.png"


def find_layer(layers: list[dict], layer_id: str) -> dict | None:
    for layer in layers:
        if layer.get("id") == layer_id:
            return layer
        found = find_layer(layer.get("children", []), layer_id)
        if found:
            return found
    return None


def walk_layers(layers: list[dict]):
    for layer in layers:
        yield layer
        yield from walk_layers(layer.get("children", []))


# ---------------------------------------------------------------------------
# TRF certificate privacy: Candidate Number, TRF Number, passport/ID are blurred before any use
# ---------------------------------------------------------------------------

def blur_trf_sensitive_regions(image_path: str | Path, boxes: list[dict]) -> Path:
    """Pixelate + Gaussian blur (irreversible). boxes: [{"x","y","w","h"}] as 0..1 fractions (Claude reads them off the image)."""
    if not boxes:
        raise ValueError("Blur maydonlari berilmagan")
    src = resolve(image_path)
    img = Image.open(src).convert("RGB")
    width, height = img.size
    pad_x, pad_y = 0.02, 0.01
    for r in boxes:
        box = (
            max(0, int((r["x"] - pad_x) * width)),
            max(0, int((r["y"] - pad_y) * height)),
            min(width, int((r["x"] + r["w"] + pad_x) * width)),
            min(height, int((r["y"] + r["h"] + pad_y) * height)),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        crop = img.crop(box)
        small = crop.resize((max(1, crop.width // 24), max(1, crop.height // 24)), Image.BILINEAR)
        img.paste(small.resize(crop.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(12)), box)
    out_path = DRAFTS_DIR / f"{src.stem}_blurred.png"
    img.save(out_path)
    print(f"[maxfiylik] {len(boxes)} ta maydon xiralashtirildi -> {rel(out_path)} (ko'z bilan tekshiring!)")
    return out_path


def _parse_boxes(boxes: list[str]) -> list[dict]:
    return [dict(zip("xywh", (float(v) for v in b.split(",")))) for b in boxes]


# ---------------------------------------------------------------------------
# new / edit
# ---------------------------------------------------------------------------

def _template(poster_type: str, from_id: str | None) -> dict:
    if from_id:
        src = load_spec(from_id)
        keep = ("base", "formats", "canvas", "styles", "layers", "art", "texts")
        return {k: copy.deepcopy(src[k]) for k in keep if k in src} | {"images": {"logo": {"file": BRAND["brand"]["logo_full"]}}}
    path = TEMPLATES_DIR / f"{poster_type}.json"
    if path.exists():
        tpl = json.loads(path.read_text(encoding="utf-8"))
        tpl.pop("_about", None)
        return tpl
    print(f"[ogohlantirish] {rel(path)} yo'q — bo'sh maket (faqat logotip). Qatlamlarni Claude yozadi.")
    return {
        "base": "feed", "formats": {"feed": {}, "story": {}}, "canvas": "$background_card", "styles": {},
        "layers": [{"id": "logo", "type": "image", "image": "logo", "x": 80, "y": 64, "h": 88, "w": "auto", "fit": "FIT"}],
        "art": {"description": ""}, "texts": {},
    }


def new_poster(args) -> None:
    if spec_path(args.id).exists() and not args.force:
        raise SystemExit(f"{args.id} allaqachon bor (qayta yaratish uchun --force, o'zgartirish uchun `edit`)")
    tpl = _template(args.type, args.from_id)
    texts = tpl.pop("texts", {})
    if args.texts:
        texts = json.loads(resolve(args.texts).read_text(encoding="utf-8"))
    texts.update(_parse_sets(args.set))
    spec = {
        "poster_id": args.id,
        "poster_type": args.type,
        "title": args.title or args.id.replace("_", " ").title(),
        "mode": "reference" if args.reference else "wishes",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        **tpl,
        "texts": texts,
        "source": {"reference": None, "wishes": args.wishes or "", "assets": []},
        "parity": None,
        "figma": {"file_key": FIGMA["file_key"], "page": args.id, "nodes": {}, "bounds": {}},
        "outputs": {},
    }
    spec.setdefault("images", {}).setdefault("logo", {"file": BRAND["brand"]["logo_full"]})
    spec["images"].setdefault("art", {"file": None})
    if args.formats:
        spec["formats"] = {f: spec.get("formats", {}).get(f, {}) for f in args.formats.split(",")}
    for item in args.asset:
        file, _, role = item.partition("::")
        if not resolve(file).exists():
            raise SystemExit(f"Asset topilmadi: {file}")
        spec["source"]["assets"].append({"file": rel(resolve(file)), "role": role or "an object to use exactly as it looks"})
    if args.wishes:
        spec["art"]["description"] = spec["art"].get("description") or ""

    if args.reference:
        ref = resolve(args.reference)
        out_dir = REFS_DIR / args.id
        info = poster_reference.analyze(ref, out_dir)
        spec["base"] = info["base"]
        spec["source"]["reference"] = rel(ref)
        spec["parity"] = {
            "reference": rel(ref),
            "design": rel(out_dir / "reference_design.png"),
            "grid": rel(out_dir / "reference_grid.png"),
            "palette": info["palette"],
            "text_boxes": [],
            "deviations": [],
        }
        # Other formats get their own artwork, extended from the parity artwork (same scene, taller/shorter frame)
        for fmt in spec["formats"]:
            if fmt != spec["base"]:
                over = spec["formats"].setdefault(fmt, {}).setdefault("overrides", {})
                over["art"] = {**over.get("art", {}), "image": f"art_{fmt}", "y": 0, "h": "auto"}
                spec["images"].setdefault(f"art_{fmt}", {"file": None})
        spec["art"] = {"description": "", "replace": [], "keep_clear": ""}

    save_spec(spec, f"new ({spec['mode']})")
    print(f"[spec] {rel(spec_path(args.id))} — {spec['mode']}, base {spec['base']}, formats {', '.join(spec['formats'])}")
    if args.reference:
        print(f"""
Reference parity — keyingi qadamlar (Claude):
  1. {spec['parity']['grid']} ni och: koordinatalar to'g'ridan-to'g'ri Figma px ({spec['base']} {FORMATS[spec['base']]['size']}).
  2. Matn/logo bloklarini o'lcha: python scripts/poster_reference.py measure --image {spec['parity']['design']} \\
       --box title=x,y,w,h --box subtitle=... --out {rel(REFS_DIR / args.id / 'measure.png')}
  3. Spec'ni yoz: layers (joy, o'lcham, shrift, rang, harf oralig'i referencedagidek), styles, canvas,
     parity.text_boxes (referencedagi barcha matn/logo/ikonka qutilari), art.description (sahna tavsifi),
     art.replace (masalan: "Replace the reference's golden cup with the exact silver trophy from reference image 2.").
  4. python scripts/poster_studio.py art --id {args.id}""")
    else:
        print(f"\nKeyingi qadam: spec'dagi art.description ni foydalanuvchi istagidan yoz, kerak bo'lsa layers ni moslashtir, "
              f"keyin: python scripts/poster_studio.py art --id {args.id}")


def _parse_sets(pairs: list[str]) -> dict:
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"key=value formatida bo'lishi kerak: {pair}")
        key, value = pair.split("=", 1)
        out[key.strip()] = value.replace("\\n", "\n")
    return out


def _value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.replace("\\n", "\n")  # shell'dan "\n" -> qator ko'chishi


def _set_path(node: dict, path: list[str], value) -> None:
    for part in path[:-1]:
        node = node.setdefault(part, {})
    if value is None:
        node.pop(path[-1], None)
    else:
        node[path[-1]] = value


def edit_poster(args) -> None:
    spec = load_spec(args.id)
    notes, layout_changed = [], False
    for key, value in _parse_sets(args.set).items():
        if key not in spec["texts"]:
            print(f"[ogohlantirish] yangi matn kaliti '{key}' — u biror qatlamda {{{key}}} sifatida ishlatilishi kerak")
        spec["texts"][key] = value
        notes.append(f'{key}="{value}"')
    for item in args.layer:
        target, raw = item.split("=", 1)
        value = _value(raw)
        fmt, _, target = target.rpartition(":")
        path = target.split(".")
        if path[0] in ("styles", "art", "canvas", "images", "source"):
            _set_path(spec, path, value)
        elif fmt:
            _set_path(spec.setdefault("formats", {}).setdefault(fmt, {}).setdefault("overrides", {}), path, value)
        else:
            layer = find_layer(spec["layers"], path[0])
            if not layer:
                raise SystemExit(f"Qatlam topilmadi: {path[0]} (bor: {', '.join(l['id'] for l in walk_layers(spec['layers']))})")
            _set_path(layer, path[1:], value)
        notes.append(item)
        layout_changed = True
    notes += args.change
    layout_changed |= bool(args.change)
    if spec.get("parity") and layout_changed:
        # Reference parity stays the baseline; every requested change is a logged deviation from it
        spec["parity"]["deviations"].append({"at": datetime.now().isoformat(timespec="seconds"),
                                             "request": args.request or "; ".join(args.change) or "", "changes": notes})
    save_spec(spec, "edit: " + "; ".join(notes))
    print(f"[spec] {args.id}: {'; '.join(notes)}")
    if layout_changed:
        print(f"Keyingi qadam: python scripts/poster_studio.py figma --id {args.id}  (to'liq qayta chizish, eski versiya arxivda qoladi)")
    else:
        print(f"Keyingi qadam: python scripts/poster_studio.py figma --id {args.id} --texts  (faqat matnlar, ~2 soniya)")


def set_image(args) -> None:
    """Photo / element / TRF / emoji as a spec image (images.<name>), used by an image layer."""
    spec = load_spec(args.id)
    file = resolve(args.file)
    if not file.exists():
        raise SystemExit(f"Fayl topilmadi: {args.file}")
    entry = {"file": rel(file)}
    if args.trf:
        if not args.blur_box and POSTER_SETTINGS.get("auto_blur_trf_candidate_id", True):
            raise SystemExit("TRF uchun --blur-box x,y,w,h (0..1) kerak: Candidate Number, TRF Number, pasport/ID, "
                             "tug'ilgan sana, shtrix-kod. Rasmni ko'rib qutilarni ber.")
        entry = {"file": rel(blur_trf_sensitive_regions(file, _parse_boxes(args.blur_box))), "source": rel(file), "trf": True}
    spec.setdefault("images", {})[args.name] = entry
    save_spec(spec, f"image {args.name} = {entry['file']}")
    print(f"[spec] images.{args.name} = {entry['file']} — qatlam: {{\"type\": \"image\", \"image\": \"{args.name}\", ...}}")


# ---------------------------------------------------------------------------
# Flow artwork
# ---------------------------------------------------------------------------

def art_request(args) -> None:
    spec = load_spec(args.id)
    if not args.change and not spec["art"].get("description"):
        raise SystemExit("spec.art.description bo'sh — sahna tavsifini yoz (referencedan yoki foydalanuvchi istagidan).")
    clean = None
    if spec["mode"] == "reference" and not args.change:
        boxes = spec["parity"].get("text_boxes") or []
        if not boxes:
            raise SystemExit("parity.text_boxes bo'sh — referencedagi barcha matn/logo/ikonka qutilarini [x,y,w,h] (design px) yoz.")
        clean = poster_reference.clean_plate(resolve(spec["parity"]["design"]), boxes, REFS_DIR / args.id / "reference_clean.png")
        spec["parity"]["clean_plate"] = rel(clean)
        print(f"[parity] clean plate: {rel(clean)} — ochib tekshir: hech qanday harf qolmagan bo'lsin")
    scenes, targets = art_scenes(spec, clean, args.change, args.variants)
    request = _write_request(f"{args.id}_art", scenes, targets)
    if args.change:
        spec["art"].setdefault("changes", []).append(args.change)
        if spec.get("parity"):
            spec["parity"]["deviations"].append({"at": datetime.now().isoformat(timespec="seconds"),
                                                 "request": args.change, "changes": ["art"]})
    save_spec(spec, f"art request {rel(request)}" + (f" (change: {args.change})" if args.change else ""))
    print(f"\nKeyingi qadam: flow_generate -> flow_wait -> python scripts/flow_assets.py import {rel(request)}")


def import_art(target: dict, found: Path, project: str) -> None:
    """Called by flow_assets.py import for kind=poster_art."""
    spec = load_spec(target["poster_id"])
    name = target["image"]
    dest = ROOT / "assets/ai_generated/posters_bg" / f"{spec['poster_id']}_{name}_{datetime.now():%m%d_%H%M%S}{found.suffix.lower()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(found.read_bytes())
    spec.setdefault("images", {})[name] = {"file": rel(dest)}
    save_spec(spec, f"art {name} <- {project}")
    print(f"[flow] {spec['poster_id']}.images.{name} -> {rel(dest)}  (ochib tekshir: matn/harf yo'q bo'lsin)")


# ---------------------------------------------------------------------------
# Figma images (upload_assets)
# ---------------------------------------------------------------------------

def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _cache() -> dict:
    return json.loads(IMAGE_CACHE.read_text(encoding="utf-8")) if IMAGE_CACHE.exists() else {}


def used_images(spec: dict) -> list[str]:
    names = []
    for fmt in spec["formats"]:
        for layer in walk_layers(format_layers(spec, fmt)):
            if layer.get("type") == "image" and layer["image"] not in names:
                names.append(layer["image"])
    return names


def pending_uploads(spec: dict) -> list[str]:
    cache, pending = _cache(), []
    file_key = spec["figma"]["file_key"]
    for name in used_images(spec):
        entry = spec["images"].get(name) or {}
        if not entry.get("file") or not resolve(entry["file"]).exists():
            raise SystemExit(f"images.{name} fayli yo'q — avval `art` (Flow) yoki `image --name {name}`.")
        sha = _sha1(resolve(entry["file"]))
        hit = cache.get(f"{file_key}:{sha}")
        if hit:
            entry.update({"hash": hit["hash"], "sha1": sha, "file_key": file_key})
        elif not (entry.get("hash") and entry.get("sha1") == sha and entry.get("file_key") == file_key):
            pending.append(name)
    return pending


def upload(args) -> None:
    spec = load_spec(args.id)
    pending = pending_uploads(spec)
    if not args.url:
        save_spec(spec)
        if not pending:
            print("Barcha rasmlar Figma faylida bor. Keyingi qadam: python scripts/poster_studio.py figma --id " + args.id)
            return
        print(f"Yuklanadigan rasmlar ({len(pending)}): " + ", ".join(f"{n} ({spec['images'][n]['file']})" for n in pending))
        print(f"upload_assets(fileKey=\"{spec['figma']['file_key']}\", count={len(pending)}) -> submitUrl'larni shu tartibda bering:")
        print(f"python scripts/poster_studio.py upload --id {args.id} " + " ".join(f"--url <submitUrl{i + 1}>" for i in range(len(pending))))
        return
    if len(args.url) != len(pending):
        raise SystemExit(f"{len(pending)} ta URL kerak ({', '.join(pending)}), {len(args.url)} ta berildi.")
    cache = _cache()
    file_key = spec["figma"]["file_key"]
    for name, url in zip(pending, args.url):
        path = resolve(spec["images"][name]["file"])
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        upload_name = f"{spec['poster_id']}_{name}{path.suffix.lower()}"
        res = subprocess.run(["curl", "-s", "-X", "POST", "-F", f"file=@{path.as_posix()};type={mime};filename={upload_name}", url],
                             capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        if not data.get("success"):
            raise SystemExit(f"Yuklash xatosi ({name}): {res.stdout}")
        sha = _sha1(path)
        spec["images"][name].update({"hash": data["imageHash"], "sha1": sha, "file_key": file_key})
        spec["figma"].setdefault("cleanup", []).append(data.get("placedOnNodeId"))
        cache[f"{file_key}:{sha}"] = {"hash": data["imageHash"], "file": rel(path)}
        print(f"[figma] {name} -> {data['imageHash']}")
    IMAGE_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    save_spec(spec, "upload " + ", ".join(pending))
    print(f"Keyingi qadam: python scripts/poster_studio.py figma --id {args.id}")


# ---------------------------------------------------------------------------
# Spec -> Figma document (resolved layers per format)
# ---------------------------------------------------------------------------

def hex_color(value: str) -> str:
    value = COLORS.get(value[1:], value) if value.startswith("$") else value
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise SystemExit(f"Rang noto'g'ri: {value} (#RRGGBB yoki $brand_token)")
    return value


def rgb(value: str) -> dict:
    h = hex_color(value)
    return {"r": int(h[1:3], 16) / 255, "g": int(h[3:5], 16) / 255, "b": int(h[5:7], 16) / 255}


def paints(spec_fill) -> list | None:
    """'#hex' | '$token' | {"color","opacity"} | {"gradient": angle_deg, "stops": [[color, pos, alpha?], ...]} | list."""
    if spec_fill is None:
        return None
    if isinstance(spec_fill, list):
        return [p for f in spec_fill for p in paints(f)]
    if isinstance(spec_fill, str):
        return [{"type": "SOLID", "color": rgb(spec_fill)}]
    if "gradient" in spec_fill or "radial" in spec_fill:
        stops = [{"position": s[1], "color": {**rgb(s[0]), "a": s[2] if len(s) > 2 else 1}} for s in spec_fill["stops"]]
        if "radial" in spec_fill:
            return [{"type": "GRADIENT_RADIAL", "gradientTransform": [[1, 0, 0], [0, 1, 0]], "gradientStops": stops,
                     "opacity": spec_fill.get("opacity", 1)}]
        a = math.radians(spec_fill["gradient"])  # 0 = left -> right, 90 = top -> bottom
        c, s = round(math.cos(a), 6), round(math.sin(a), 6)
        transform = [[c, s, 0.5 - 0.5 * (c + s)], [-s, c, 0.5 - 0.5 * (c - s)]]
        return [{"type": "GRADIENT_LINEAR", "gradientTransform": transform, "gradientStops": stops,
                 "opacity": spec_fill.get("opacity", 1)}]
    return [{"type": "SOLID", "color": rgb(spec_fill["color"]), "opacity": spec_fill.get("opacity", 1)}]


def effects(items: list[dict] | None) -> list | None:
    if not items:
        return None
    out = []
    for e in items:
        if "bg_blur" in e:
            out.append({"type": "BACKGROUND_BLUR", "radius": e["bg_blur"], "visible": True})
        elif "blur" in e:
            out.append({"type": "LAYER_BLUR", "radius": e["blur"], "visible": True})
        else:
            kind = "INNER_SHADOW" if "inner_shadow" in e else "DROP_SHADOW"
            out.append({"type": kind, "color": {**rgb(e.get("shadow") or e.get("inner_shadow")), "a": e.get("alpha", 0.5)},
                        "offset": {"x": e.get("x", 0), "y": e.get("y", 0)}, "radius": e.get("radius", e.get("blur_radius", 12)),
                        "spread": e.get("spread", 0), "visible": True, "blendMode": "NORMAL"})
    return out


def icon_svg(name: str, color: str, size: int) -> str:
    prefix, icon = name.split(":", 1)
    color = hex_color(color)
    if prefix == "lucide":
        path = ICONS_DIR / "lucide-static/icons" / f"{icon}.svg"
        if not path.exists():
            raise SystemExit(f"Lucide ikonkasi yo'q: {icon} (https://lucide.dev/icons)")
        svg = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S).strip()
        svg = re.sub(r'\s+class="[^"]*"', "", svg)
        return (svg.replace('width="24"', f'width="{size}"', 1).replace('height="24"', f'height="{size}"', 1)
                .replace('stroke="currentColor"', f'stroke="{color}"'))
    if prefix in ("simple-icons", "si"):
        data = json.loads((ICONS_DIR / "@iconify-json/simple-icons/icons.json").read_text(encoding="utf-8"))
        icon = data.get("aliases", {}).get(icon, {}).get("parent", icon)
        if icon not in data["icons"]:
            raise SystemExit(f"Simple Icons'da yo'q: {icon} (https://simpleicons.org)")
        body = data["icons"][icon]["body"].replace('fill="currentColor"', f'fill="{color}"')
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24">{body}</svg>'
    raise SystemExit(f"Ikonka manbasi noma'lum: {name} (lucide:<nom> yoki simple-icons:<nom>)")


def format_layers(spec: dict, fmt: str) -> list[dict]:
    """Base layers moved to `fmt`: top/bottom anchored layers shift by the formats' margin difference, then overrides."""
    layers = copy.deepcopy(spec["layers"])
    base = spec["base"]
    if fmt != base:
        dt = FORMATS[fmt]["margin"]["top"] - FORMATS[base]["margin"]["top"]
        db = FORMATS[fmt]["margin"]["bottom"] - FORMATS[base]["margin"]["bottom"]
        for layer in layers:
            if layer.get("shift", True):
                if isinstance(layer.get("y"), (int, float)):
                    layer["y"] += dt
                if isinstance(layer.get("bottom"), (int, float)):
                    layer["bottom"] += db
    for layer_id, props in spec.get("formats", {}).get(fmt, {}).get("overrides", {}).items():
        layer = find_layer(layers, layer_id)
        if layer is None:
            raise SystemExit(f"formats.{fmt}.overrides: qatlam topilmadi '{layer_id}'")
        for k, v in props.items():
            if v is None:
                layer.pop(k, None)
            else:
                layer[k] = v

    def keep(items):
        return [dict(l, children=keep(l["children"])) if "children" in l else l
                for l in items if fmt in l.get("formats", [fmt])]
    return keep(layers)


def _segments(template: str, texts: dict, ranges: dict) -> list[dict]:
    segs = []
    for part in re.split(r"(\{[A-Za-z0-9_]+\})", template):
        if not part:
            continue
        m = re.fullmatch(r"\{(\w+)\}", part)
        if m:
            if m[1] not in texts:
                raise SystemExit(f"Matn kaliti yo'q: {m[1]} (texts'ga qo'sh: --set {m[1]}=...)")
            seg = {"text": texts[m[1]], "key": m[1]}
            r = ranges.get(m[1], {})
            for k in ("style", "font", "size", "letterSpacing"):
                if k in r:
                    seg[k] = r[k]
            if "color" in r:
                seg["fills"] = paints(r["color"])
            segs.append(seg)
        else:
            segs.append({"text": part})
    return segs


def resolve_doc(spec: dict, mode: str = "render", require_hashes: bool = True) -> dict:
    texts, icons, used_styles = spec["texts"], {}, {}
    images_meta = {}

    def icon_key(name: str, color: str, size: int) -> str:
        key = f"{name}|{hex_color(color)}|{size}"
        if key not in icons:
            icons[key] = {"name": f"Icon/{name.split(':', 1)[1]} {size}", "size": size, "svg": icon_svg(name, color, size)}
        return key

    def image_size(name: str) -> tuple[int, int]:
        entry = spec["images"].get(name) or {}
        if not entry.get("file"):
            raise SystemExit(f"images.{name} yo'q")
        if name not in images_meta:
            with Image.open(resolve(entry["file"])) as im:
                images_meta[name] = {"w": im.width, "h": im.height, "hash": entry.get("hash")}
        return images_meta[name]["w"], images_meta[name]["h"]

    def num(value, total):
        if isinstance(value, str) and value.endswith("%"):
            return round(float(value[:-1]) / 100 * total, 2)
        return value

    def norm(layer: dict, W: int, H: int) -> dict:
        t = layer["type"]
        out = {"id": layer["id"], "type": t}
        for k in ("name", "radius", "opacity", "locked", "hidden", "absolute", "centerX", "centerY"):
            if k in layer:
                out[k] = layer[k]
        for k, total in (("x", W), ("w", W), ("right", W), ("y", H), ("h", H), ("bottom", H)):
            if k in layer and layer[k] not in ("auto", "fill"):
                out[k] = num(layer[k], total)
        if layer.get("w") == "fill":
            out["fill"] = True
        if "blend" in layer:
            out["blend"] = layer["blend"].upper()
        if layer.get("fill") is not None and t != "text":
            out["fills"] = paints(layer["fill"])
        if layer.get("stroke"):
            out["strokes"] = paints({"color": layer["stroke"]["color"], "opacity": layer["stroke"].get("opacity", 1)})
            out["strokeWeight"] = layer["stroke"].get("weight", 1)
        if layer.get("effects"):
            out["effects"] = effects(layer["effects"])

        if t == "image":
            out["image"] = layer["image"]
            out["fit"] = layer.get("fit", "FILL").upper()
            iw, ih = image_size(layer["image"])
            if layer.get("h") == "auto" or "h" not in layer:
                out["h"] = round(out["w"] * ih / iw, 2)
            if layer.get("w") == "auto" or "w" not in layer:
                out["w"] = round(out["h"] * iw / ih, 2)
        elif t == "text":
            out.update({
                "font": layer.get("font", HEADING_FONT), "style": layer.get("style", "Regular"), "size": layer.get("size", 32),
                "fills": paints(layer.get("color", "#FFFFFF")),
                "segments": _segments(layer["text"], texts, layer.get("ranges", {})),
            })
            for k in ("lineHeight", "letterSpacing"):
                if k in layer:
                    out[k] = layer[k]
            if "align" in layer:
                out["align"] = {"left": "LEFT", "center": "CENTER", "right": "RIGHT", "justify": "JUSTIFIED"}[layer["align"]]
            if layer.get("case"):
                out["case"] = {"upper": "UPPER", "lower": "LOWER", "title": "TITLE"}[layer["case"]]
        elif t == "icon":
            out["icon"] = icon_key(layer["icon"], layer.get("color", "$brand_glow"), layer.get("size", 32))
        elif t == "item":
            st = spec["styles"][layer["style"]]
            out["style"] = layer["style"]
            out["icon"] = icon_key(layer["icon"], st.get("icon_color", "$brand_glow"), st.get("icon_size", 32))
            out["text"] = "".join(s["text"] for s in _segments(layer["text"], texts, {}))
            used_styles.setdefault(layer["style"], (out["icon"], out["text"]))
        elif t == "stack":
            out["direction"] = layer.get("direction", "vertical").upper()
            out["gap"] = layer.get("gap", 0)
            if "padding" in layer:
                p = layer["padding"]
                out["padding"] = [p] * 4 if isinstance(p, (int, float)) else p
            if "justify" in layer:
                out["justify"] = {"start": "MIN", "center": "CENTER", "end": "MAX", "between": "SPACE_BETWEEN"}[layer["justify"]]
            if "align" in layer:
                out["align"] = {"start": "MIN", "center": "CENTER", "end": "MAX", "baseline": "BASELINE"}[layer["align"]]
            out["children"] = [norm(c, W, H) for c in layer.get("children", [])]
        return out

    frames = []
    for fmt in spec["formats"]:
        W, H = FORMATS[fmt]["size"]
        frames.append({
            "fmt": fmt, "name": f"{spec['title']} — {fmt.capitalize()} {W}x{H}", "W": W, "H": H,
            "fills": paints(spec.get("canvas", "$background_card")),
            "layers": [norm(l, W, H) for l in format_layers(spec, fmt)],
            **({"safe": FORMATS[fmt]["safe"]} if FORMATS[fmt].get("safe") else {}),
        })

    styles = {}
    for name, st in spec.get("styles", {}).items():
        sample = used_styles.get(name)
        pad = st.get("padding", 0)
        styles[name] = {
            "title": st.get("title", name), "description": st.get("description", ""), "used": bool(sample),
            "direction": st.get("direction", "horizontal").upper(), "gap": st.get("gap", 12),
            "padding": [pad] * 4 if isinstance(pad, (int, float)) else pad,
            "radius": st.get("radius"), "fills": paints(st.get("fill")) or [],
            "strokes": paints({"color": st["stroke"]["color"], "opacity": st["stroke"].get("opacity", 1)}) if st.get("stroke") else None,
            "strokeWeight": (st.get("stroke") or {}).get("weight", 1), "effects": effects(st.get("effects")),
            "font": st.get("font", HEADING_FONT), "style": st.get("style", "Medium"), "size": st.get("size", 28),
            "textFills": paints(st.get("color", "#FFFFFF")), "letterSpacing": st.get("letterSpacing"),
            "sample_icon": sample[0] if sample else None, "sample_text": sample[1] if sample else "",
        }

    if require_hashes:
        missing = [n for n, m in images_meta.items() if not m["hash"]]
        if missing or pending_uploads(spec):
            raise SystemExit(f"Figma'ga yuklanmagan rasmlar: {', '.join(missing or pending_uploads(spec))} — avval "
                             f"python scripts/poster_studio.py upload --id {spec['poster_id']}")
    return {
        "poster_id": spec["poster_id"], "title": spec["title"], "page": spec["figma"].get("page") or spec["poster_id"],
        "mode": mode, "stamp": datetime.now().strftime("%m-%d %H:%M"),
        "frames": frames, "icons": icons, "styles": styles,
        "images": {n: {"hash": m["hash"]} for n, m in images_meta.items()},
        "cleanup": [c for c in spec["figma"].get("cleanup", []) if c],
        "targets": spec["figma"].get("nodes", {}),
    }


def figma_script(args) -> None:
    spec = load_spec(args.id)
    mode = "texts" if args.texts else "render"
    if mode == "texts" and not spec["figma"].get("nodes"):
        raise SystemExit("Figma'da hali frame yo'q — avval to'liq render: figma --id " + args.id)
    pending_uploads(spec)  # refresh cached hashes
    doc = resolve_doc(spec, mode)
    if mode == "texts":
        # Texts mode touches only text layers and item labels: no icons/styles/images needed in the payload
        doc.update(icons={}, styles={}, images={}, cleanup=[])
    code =RENDERER.read_text(encoding="utf-8").replace("const DOC = __DOC__;", "const DOC = " + json.dumps(doc, ensure_ascii=False) + ";", 1)
    out = FIGMA_DIR / f"{args.id}{'_texts' if args.texts else ''}.js"
    out.write_text(code, encoding="utf-8")
    save_spec(spec)
    print(f"[figma] {rel(out)} ({len(code) // 1024} KB) — {mode}")
    print(f"use_figma(fileKey=\"{spec['figma']['file_key']}\", code=<{rel(out)} mazmuni>, skillNames=\"figma-use,figma-generate-design\")")
    print(f"Natija JSON'ini saqla: python scripts/poster_studio.py record --id {args.id} --result <fayl yoki JSON>")


def record(args) -> None:
    spec = load_spec(args.id)
    raw = args.result
    data = json.loads(resolve(raw).read_text(encoding="utf-8") if not raw.lstrip().startswith("{") else raw)
    fig = spec["figma"]
    if data.get("mode") == "render":
        fig.update({"page_id": data["page"], "nodes": data["frames"], "kit": data["kit"]})
        fig["cleanup"] = []
        fig.setdefault("archived", []).extend(data.get("archived", []))
    fig["bounds"] = data.get("bounds", {})
    save_spec(spec, f"figma {data.get('mode')}: " + (", ".join(data.get("changed", [])) or ", ".join(f"{k}={v}" for k, v in fig["nodes"].items())))
    print("[figma] " + ", ".join(f"{fmt} -> {node}" for fmt, node in fig["nodes"].items()))
    print("Keyingi qadam: download_assets(fileKey, nodeId, defaultFormat=\"png\", defaultScale=1) har bir frame uchun, keyin:")
    print(f"python scripts/poster_studio.py export --id {args.id} " + " ".join(f"--url {fmt}=<export.url>" for fmt in fig["nodes"]))
    _check_bounds(spec)


# ---------------------------------------------------------------------------
# Export + verification
# ---------------------------------------------------------------------------

def export(args) -> None:
    spec = load_spec(args.id)
    for item in args.url:
        fmt, url = item.split("=", 1)
        dest = output_path(args.id, fmt)
        req = urllib.request.Request(url, headers={"User-Agent": "impulse-pipeline"})
        with urllib.request.urlopen(req, timeout=120) as res:
            dest.write_bytes(res.read())
        with Image.open(dest) as im:
            if im.size != FORMATS[fmt]["size"]:
                raise SystemExit(f"{fmt}: o'lcham {im.size}, kutilgan {FORMATS[fmt]['size']} — download_assets scale=1 bilan qayta")
        spec["outputs"][fmt] = rel(dest)
        print(f"[export] {fmt} -> {rel(dest)}")
    save_spec(spec, "export " + ", ".join(spec["outputs"]))
    verify(spec)


def _check_bounds(spec: dict) -> list[str]:
    problems = []
    for fmt, bounds in spec["figma"].get("bounds", {}).items():
        W, H = FORMATS[fmt]["size"]
        safe = FORMATS[fmt].get("safe", {"top": 0, "bottom": 0})
        for layer_id, (x, y, w, h) in bounds.items():
            if y < safe["top"] or y + h > H - safe["bottom"]:
                problems.append(f"{fmt}:{layer_id} Instagram UI zonasida (y {y}..{y + h}, xavfsiz {safe['top']}..{H - safe['bottom']})")
            if x < 40 or x + w > W - 40:
                problems.append(f"{fmt}:{layer_id} chetga juda yaqin (x {x}..{x + w})")
    for p in problems:
        print("[ogohlantirish] " + p)
    return problems


def _expected_texts(spec: dict) -> dict[str, dict[str, str]]:
    doc = resolve_doc(spec, require_hashes=False)
    out = {}
    for fr in doc["frames"]:
        found = {}
        for layer in walk_layers(fr["layers"]):
            if layer["type"] == "text":
                found[layer["id"]] = "".join(s["text"] for s in layer["segments"])
            elif layer["type"] == "item":
                found[layer["id"]] = layer["text"]
        out[fr["fmt"]] = found
    return out


def verify(spec: dict) -> None:
    """Check sheet: every text layer cropped from the export at 2x next to the expected text (read it letter by letter)."""
    expected = _expected_texts(spec)
    tiles = []
    for fmt, path in spec["outputs"].items():
        img = Image.open(resolve(path)).convert("RGB")
        for layer_id, (x, y, w, h) in spec["figma"].get("bounds", {}).get(fmt, {}).items():
            crop = img.crop((max(0, x - 14), max(0, y - 10), min(img.width, x + w + 14), min(img.height, y + h + 10)))
            scale = min(2.0, 1000 / crop.width)
            crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.LANCZOS)
            label = f"{fmt}:{layer_id}  ->  {expected.get(fmt, {}).get(layer_id, '(logo)')!r}"
            head = Image.new("RGB", (1000, 30), (24, 24, 24))
            ImageDraw.Draw(head).text((8, 6), label.replace("\n", " / "), fill=(255, 220, 90), font=poster_reference._font(16))
            tiles += [head, crop]
    if tiles:
        sheet = Image.new("RGB", (1000, sum(t.height for t in tiles) + 6 * len(tiles)), (0, 0, 0))
        y = 0
        for t in tiles:
            sheet.paste(t, (0, y))
            y += t.height + 6
        out = DRAFTS_DIR / f"{spec['poster_id']}_check.png"
        sheet.save(out)
        print(f"\n[verify] matn varag'i: {rel(out)} — har bir qatorni kutilgan matn bilan harfma-harf solishtir")
    problems = _check_bounds(spec)
    if spec.get("parity") and spec["outputs"].get(spec["base"]):
        scores = poster_reference.compare(resolve(spec["parity"]["design"]), resolve(spec["outputs"][spec["base"]]),
                                          REFS_DIR / spec["poster_id"] / f"parity_{spec['base']}.png")
        print(f"[parity] layout {scores['layout']} / rang {scores['color']} (100 = bir xil) — varaq: {rel(Path(scores['sheet']))}")
        for d in spec["parity"]["deviations"]:
            print(f"   ruxsat etilgan farq ({d['at']}): {d['request'] or '; '.join(d['changes'])}")
    print("Tekshiruv: logotip buzilmagan, matnlar aynan, xavfsiz zona" + (" — muammo bor!" if problems else " — OK"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Impulse Poster Studio — Figma + Google Flow")
    sub = p.add_subparsers(dest="command", required=True)

    n = sub.add_parser("new", help="Yangi poster spec (reference parity yoki istak bo'yicha)")
    n.add_argument("--id", required=True)
    n.add_argument("--type", required=True, choices=["announcement", "promo", "result", "carousel", "cover"])
    n.add_argument("--title", help="Figma'dagi nom (standart: id)")
    n.add_argument("--reference", help="100%% parity uchun reference poster")
    n.add_argument("--from", dest="from_id", help="Boshqa posterning maketidan boshlash")
    n.add_argument("--wishes", help="Foydalanuvchi istagi (erkin matn)")
    n.add_argument("--texts", help="Matnlar JSON {kalit: matn}")
    n.add_argument("--set", action="append", default=[], help="kalit=matn")
    n.add_argument("--asset", action="append", default=[], help="fayl::rol — Flow'ga beriladigan asset (kubok, foto)")
    n.add_argument("--formats", help="feed,story (standart: shablondagi)")
    n.add_argument("--force", action="store_true")

    e = sub.add_parser("edit", help="Matn / qatlam / uslubni o'zgartirish")
    e.add_argument("--id", required=True)
    e.add_argument("--set", action="append", default=[], help="matn_kaliti=yangi matn")
    e.add_argument("--layer", action="append", default=[], help="[fmt:]qatlam.xossa=qiymat | styles.chip.radius=24 | art.description=...")
    e.add_argument("--change", action="append", default=[], help="Erkin izoh (spec'ni Claude o'zgartirgan bo'lsa)")
    e.add_argument("--request", help="Foydalanuvchining so'zi (parity deviatsiyasi uchun)")

    i = sub.add_parser("image", help="Foto / element / TRF rasmini spec'ga qo'shish")
    i.add_argument("--id", required=True)
    i.add_argument("--name", required=True)
    i.add_argument("--file", required=True)
    i.add_argument("--trf", action="store_true", help="IELTS TRF: maxfiy maydonlar blur qilinadi")
    i.add_argument("--blur-box", action="append", default=[], help="x,y,w,h (0..1)")

    a = sub.add_parser("art", help="Flow artwork so'rovi (matnsiz)")
    a.add_argument("--id", required=True)
    a.add_argument("--change", help="Mavjud artworkni tahrirlash")
    a.add_argument("--variants", type=int, default=1)

    u = sub.add_parser("upload", help="Rasmlarni Figma faylga yuklash (upload_assets)")
    u.add_argument("--id", required=True)
    u.add_argument("--url", action="append", default=[], help="upload_assets submitUrl (tartib bilan)")

    f = sub.add_parser("figma", help="use_figma uchun skript")
    f.add_argument("--id", required=True)
    f.add_argument("--texts", action="store_true", help="Faqat matnlarni yangilash")

    r = sub.add_parser("record", help="use_figma natijasini saqlash")
    r.add_argument("--id", required=True)
    r.add_argument("--result", required=True, help="JSON fayl yoki JSON matn")

    x = sub.add_parser("export", help="download_assets URL'laridan PNG")
    x.add_argument("--id", required=True)
    x.add_argument("--url", action="append", required=True, help="fmt=url")

    sub.add_parser("verify", help="Matn varag'i + xavfsiz zona + parity").add_argument("--id", required=True)
    b = sub.add_parser("blur-trf", help="TRF maxfiy maydonlarini xiralashtirish")
    b.add_argument("--image", required=True)
    b.add_argument("--blur-box", action="append", required=True)
    sub.add_parser("list", help="Posterlar ro'yxati")

    args = p.parse_args()
    if args.command == "new":
        new_poster(args)
    elif args.command == "edit":
        edit_poster(args)
    elif args.command == "image":
        set_image(args)
    elif args.command == "art":
        art_request(args)
    elif args.command == "upload":
        upload(args)
    elif args.command == "figma":
        figma_script(args)
    elif args.command == "record":
        record(args)
    elif args.command == "export":
        export(args)
    elif args.command == "verify":
        verify(load_spec(args.id))
    elif args.command == "blur-trf":
        print(rel(blur_trf_sensitive_regions(args.image, _parse_boxes(args.blur_box))))
    else:
        for path in sorted(DRAFTS_DIR.glob("*.json")):
            s = json.loads(path.read_text(encoding="utf-8"))
            if "layers" in s:
                print(f"{s['poster_id']}: {s['poster_type']} [{s['mode']}] — {s.get('updated_at', '')} — "
                      f"{', '.join(s.get('outputs', {}).values()) or 'eksport kutilmoqda'}")


if __name__ == "__main__":
    main()
