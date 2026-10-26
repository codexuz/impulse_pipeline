"""
Google Flow (Nano Banana rasm + Omni/Veo video) orqali AI assetlar — so'rov yaratish va natijani import qilish.

Flow Claude Code'dagi `flow` MCP serveri orqali boshqariladi (Python undan to'g'ridan-to'g'ri chaqira olmaydi):
  1. request  -> workspace/flow_requests/<nom>.json yoziladi va flow_generate argumentlari chiqariladi
  2. Claude:   mcp__flow__flow_generate(<argumentlar>) -> mcp__flow__flow_wait(...) tugaguncha
  3. import   -> Flow yuklagan fayllar assets/ai_generated/ ga ko'chiriladi va reja/posterga yoziladi

Rasmlar (Nano Banana) bepul (0 credit). Videolar credit sarflaydi — generatsiyadan oldin
"estimated_credits" ni foydalanuvchiga ayting va ruxsat oling.

Ishlatish:
  python scripts/flow_assets.py request --plan workspace/03_edit_plans/speaking_idioms.json
  python scripts/flow_assets.py request --poster sardor_80 --image student --edit-photo
  (poster artwork: python scripts/poster_studio.py art --id <poster_id>)
  python scripts/flow_assets.py import workspace/flow_requests/speaking_idioms.json
"""
import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config/brand_preset.json").read_text(encoding="utf-8"))
FLOW = BRAND["ai_generation"]["flow"]
REQUESTS_DIR = ROOT / "workspace/flow_requests"
DRAFTS_DIR = ROOT / "workspace/05_posters/drafts"
AI_DIR = ROOT / "assets/ai_generated"

# Rasm generatori hech qachon ball, sana yoki telefon raqamini chizmasligi kerak (CLAUDE.md)
NO_TEXT_GUARD = "Absolutely no text, letters, numbers, logos or watermarks anywhere in the image."
STUDIO_PHOTO_PROMPT = (
    "Professional studio portrait of the exact same person from the reference photo: soft key light, clean dark navy "
    "studio background with a subtle electric blue rim light, natural skin tones, sharp focus, chest-up framing. "
    "Keep the face, identity, hairstyle, expression and clothing exactly the same."
)
# Flow taklif qiladigan taxminiy narx (Omni 1.1 Flash, 720p). Haqiqiy narxni Flow max_credits bilan tekshiradi
OMNI_CREDITS = {4: 7, 6: 10, 8: 12, 10: 15}


def flow_output_root() -> Path:
    return Path(os.path.expanduser(os.getenv("FLOW_OUTPUT_ROOT", FLOW["output_root"])))


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rel(path: Path) -> str:
    p = path.resolve()
    return p.relative_to(ROOT.resolve()).as_posix() if p.is_relative_to(ROOT.resolve()) else p.as_posix()


def _image_scene(prompt: str, aspect: str, references: list[str] | None = None, style: str | None = None) -> dict:
    scene = {
        "type": "image",
        "prompt": f"{prompt}. Style: {style or FLOW['default_visual_style']}. {NO_TEXT_GUARD}",
        "aspect_ratio": aspect,
        "download_quality": FLOW["download_quality"],
    }
    if references:
        scene["reference_images"] = [str(resolve(r).resolve()) for r in references]
    return scene


def _video_scene(prompt: str, seconds: float) -> dict:
    duration = next((d for d in sorted(OMNI_CREDITS) if d >= seconds), 10)
    return {
        "type": "video",
        "prompt": f"{prompt}. Vertical 9:16, {FLOW['default_visual_style']}. No on-screen text. No dialogue.",
        "aspect_ratio": "9:16",
        "model": FLOW["video_model"],
        "duration": duration,
        "resolution": "720p",
        "max_credits": FLOW["video_max_credits_per_scene"],
        "download_quality": FLOW["download_quality"],
    }


def request_for_plan(plan_path: Path, force: bool = False) -> Path:
    """edit_plan.json dagi fayli yo'q visuals (broll/sticker -> rasm, clip -> video) uchun so'rov."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    name = plan.get("id", plan_path.stem)
    scenes, targets = [], []
    for item in plan.get("visuals", []):
        if not item.get("prompt") or (item.get("file") and resolve(item["file"]).exists() and not force):
            continue
        kind = item.get("kind", "broll")
        if kind == "clip":
            scene = _video_scene(item["prompt"], float(item["end"]) - float(item["start"]))
        elif kind == "sticker":
            # Oq fon keyin shaffof qilinadi — brendning to'q fon uslubi bu yerda qo'shilmaydi
            scene = _image_scene(item["prompt"], "1:1", item.get("references"), style=FLOW["sticker_style"])
        else:
            scene = _image_scene(item["prompt"], "9:16", item.get("references"))
        scenes.append(scene)
        targets.append({"scene": len(scenes), "kind": "plan", "plan": rel(plan_path), "visual_id": item["id"], "visual_kind": kind})

    cover = plan.get("thumbnail") or {}
    if cover.get("title") and not cover.get("file"):
        # Reels muqovasi — Figma poster (matn jonli qatlam), Flow faqat matnsiz fon chizadi
        print(f"[muqova] python scripts/poster_studio.py new --id {name}_cover --type cover "
              f"--set title=\"{cover['title']}\" --set accent=\"{cover.get('accent', '')}\" --set tag=\"{cover.get('tag', '')}\"")

    return _write_request(name, scenes, targets)


def request_for_poster(poster_id: str, image: str, prompt: str | None, edit_photo: bool, references: list[str]) -> Path:
    """Poster spec rasmi (images.<image>) uchun Flow: foto -> studiya portreti yoki element/fonni tahrirlash."""
    spec = json.loads((DRAFTS_DIR / f"{poster_id}.json").read_text(encoding="utf-8"))
    entry = spec.get("images", {}).get(image) or {}
    if entry.get("trf"):
        raise SystemExit("TRF rasmi Flow'ga yuborilmaydi (maxfiylik).")
    current = entry.get("source_photo") or entry.get("file")
    if edit_photo:
        if not current:
            raise SystemExit(f"{poster_id}: images.{image} yo'q (avval poster_studio.py image --name {image} --file ...)")
        scene = _image_scene(prompt or STUDIO_PHOTO_PROMPT, "3:4", [current, *references])
    else:
        if not prompt:
            raise SystemExit("--prompt kerak")
        refs = ([current] if current and resolve(current).exists() else []) + list(references)
        scene = _image_scene(prompt, "1:1", refs[:3] or None)
    target = {"scene": 1, "kind": "poster", "poster_id": poster_id, "image": image, "edit_photo": edit_photo}
    return _write_request(f"{poster_id}_{image}", [scene], [target])


def _write_request(name: str, scenes: list[dict], targets: list[dict]) -> Path:
    if not scenes:
        raise SystemExit("Generatsiya qilinadigan narsa yo'q — barcha fayllar mavjud (qayta yaratish uchun --force).")
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    # Har bir so'rov alohida papkada — eski scene-XX fayllari bilan aralashmasligi uchun
    project = f"impulse_{name}_{datetime.now():%m%d_%H%M%S}"
    credits = sum(OMNI_CREDITS.get(s.get("duration", 8), 12) for s in scenes if s["type"] == "video")
    payload = {
        "project": project,
        "estimated_credits": credits,
        "flow_generate": {"project": project, "scenes": scenes},
        "targets": targets,
    }
    out = REQUESTS_DIR / f"{name}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    images = sum(1 for s in scenes if s["type"] == "image")
    print(f"[flow] so'rov: {rel(out)} — {images} ta rasm (0 credit), {len(scenes) - images} ta video (~{credits} credit)")
    print("mcp__flow__flow_generate argumentlari:")
    print(json.dumps(payload["flow_generate"], indent=2, ensure_ascii=False))
    return out


def _find_scene_file(project_dir: Path, scene: int, variant: int | None = None) -> Path | None:
    stem = f"scene-{scene:02d}"
    candidates = sorted(p for p in project_dir.glob(f"{stem}*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4"})
    if variant:
        chosen = [p for p in candidates if p.stem.endswith(f"-v{variant}")]
        if chosen:
            return chosen[0]
    # Bir nechta variant bo'lsa (-v1, -v2) va tanlanmagan bo'lsa — birinchisi
    return candidates[0] if candidates else None


def white_to_transparent(src: Path, out: Path, tolerance: int = 28) -> None:
    """Oq fondagi stikerni shaffof PNG ga aylantiradi: chetlardan flood-fill, ichki oq joylarga tegmaydi."""
    img = Image.open(src).convert("RGB")
    key = (255, 0, 255)
    width, height = img.size
    for xy in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        if img.getpixel(xy) != key and min(img.getpixel(xy)) > 255 - tolerance * 2:
            ImageDraw.floodfill(img, xy, key, thresh=tolerance)
    r, g, b = img.split()
    is_key = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda v: 255 if v == 255 else 0), g.point(lambda v: 255 if v == 0 else 0)),
        b.point(lambda v: 255 if v == 255 else 0),
    )
    alpha = ImageChops.invert(is_key).filter(ImageFilter.GaussianBlur(1.2))
    rgba = Image.open(src).convert("RGBA")
    rgba.putalpha(alpha)
    rgba.save(out)


def import_request(request_path: Path, variant: int | None = None, offset: int = 0) -> None:
    req = json.loads(request_path.read_text(encoding="utf-8"))
    project_dir = flow_output_root() / req["project"]
    if not project_dir.exists():
        raise SystemExit(f"Flow papkasi topilmadi: {project_dir} — flow_wait tugaganini tekshiring.")

    plans: dict[str, dict] = {}
    missing = []
    for target in req["targets"]:
        # offset: Flow bir xil papkada qayta urinishda raqamlashni davom ettiradi (scene-03, scene-04, ...)
        found = _find_scene_file(project_dir, target["scene"] + offset, variant)
        if not found:
            missing.append(target["scene"])
            continue
        is_video = found.suffix.lower() == ".mp4"

        if target["kind"] == "plan":
            plan_file = resolve(target["plan"])
            plan = plans.setdefault(target["plan"], json.loads(plan_file.read_text(encoding="utf-8")))
            vid = target["visual_id"]
            if is_video:
                dest = AI_DIR / "videos" / f"{vid}.mp4"
                _copy(found, dest)
            elif target["visual_kind"] == "sticker":
                dest = AI_DIR / "images" / f"{vid}.png"
                dest.parent.mkdir(parents=True, exist_ok=True)
                white_to_transparent(found, dest)
            else:
                dest = AI_DIR / "images" / f"{vid}{found.suffix.lower()}"
                _copy(found, dest)
            for item in plan.get("visuals", []):
                if item["id"] == vid:
                    item["file"] = rel(dest)
            print(f"[flow] {vid} -> {rel(dest)}")
        elif target["kind"] == "poster_art":
            from poster_studio import import_art
            import_art(target, found, project_dir.name)
        else:
            state_file = DRAFTS_DIR / f"{target['poster_id']}.json"
            spec = json.loads(state_file.read_text(encoding="utf-8"))
            folder = "photos" if target.get("edit_photo") else "images"
            dest = AI_DIR / folder / f"{target['poster_id']}_{target['image']}_{datetime.now():%m%d_%H%M%S}{found.suffix.lower()}"
            _copy(found, dest)
            entry = spec.setdefault("images", {}).setdefault(target["image"], {})
            if target.get("edit_photo") and entry.get("file") and not entry.get("source_photo"):
                entry["source_photo"] = entry["file"]
            entry.update({"file": rel(dest)})
            for k in ("hash", "sha1", "file_key"):
                entry.pop(k, None)
            state_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[flow] {target['poster_id']}.images.{target['image']} -> {rel(dest)} "
                  f"(keyin: poster_studio.py upload --id {target['poster_id']})")

    for name, plan in plans.items():
        resolve(name).write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    if missing:
        print(f"[ogohlantirish] Flow papkasida topilmagan sahnalar: {missing} (flow_retry yoki qayta request)")


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Flow asset ko'prigi")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("request", help="Flow uchun so'rov fayli")
    r.add_argument("--plan", help="edit_plan.json")
    r.add_argument("--poster", help="poster_id")
    r.add_argument("--image", default="photo", help="Poster spec'dagi rasm nomi (images.<nom>): photo, student, element ...")
    r.add_argument("--prompt")
    r.add_argument("--edit-photo", action="store_true", help="Mavjud fotoni studiya portretiga aylantirish")
    r.add_argument("--reference", action="append", default=[], help="Qo'shimcha reference rasm (max 3)")
    r.add_argument("--force", action="store_true")

    i = sub.add_parser("import", help="Flow natijalarini loyiha ichiga olish")
    i.add_argument("request")
    i.add_argument("--variant", type=int, help="Bir nechta variant bo'lsa — qaysi biri (1, 2, ...)")
    i.add_argument("--offset", type=int, default=0, help="Qayta urinishdagi sahna raqami siljishi (masalan, 2 -> scene-03 dan)")

    args = parser.parse_args()
    if args.command == "request":
        if args.plan:
            request_for_plan(resolve(args.plan), args.force)
        elif args.poster:
            request_for_poster(args.poster, args.image, args.prompt, args.edit_photo, args.reference)
        else:
            parser.error("--plan yoki --poster kerak")
    else:
        import_request(resolve(args.request), args.variant, args.offset)


if __name__ == "__main__":
    main()
