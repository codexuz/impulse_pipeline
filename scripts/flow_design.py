"""
Poster artwork prompts for Google Flow (Nano Banana). Flow draws ONLY the text-free artwork: hero object, scene,
light and texture. Texts, the logo, icons, chips and contacts are built by Figma as editable layers
(scripts/poster_studio.py -> scripts/figma/render_poster.js).

The prompt source depends on the spec's mode:
  - reference: "100% parity" — reference image 1 is the CLEAN PLATE of the reference poster (its texts and logo
               inpainted out), so Flow copies its composition, light, palette and mood but sees no text to copy.
               The user's own assets (trophy, photo, ...) come as references 2-3 and replace the reference's objects.
  - wishes:    the scene is described from the user's wishes (spec.art.description) + the Impulse visual style.
  - edit:      the current artwork is reference 1 and only the requested change is applied.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "config/brand_preset.json").read_text(encoding="utf-8"))
COLORS = BRAND["colors"]
FLOW = BRAND["ai_generation"]["flow"]

# margin: default distance of top/bottom-anchored content from the frame edges. When a layout is moved
# to another format, top layers shift by the difference of the `top` margins, bottom layers by the `bottom` ones.
# safe: Instagram UI bars (the Story's top 12% and bottom 14%), shown as a hidden guide in Figma.
FORMATS = {
    "feed": {"size": (1080, 1350), "flow_aspect": "3:4", "suffix": "feed_4x5", "margin": {"top": 64, "bottom": 64}},
    "story": {"size": (1080, 1920), "flow_aspect": "9:16", "suffix": "story_9x16", "margin": {"top": 252, "bottom": 270},
              "safe": {"top": 230, "bottom": 269}},
    "square": {"size": (1080, 1080), "flow_aspect": "1:1", "suffix": "square_1x1", "margin": {"top": 64, "bottom": 64}},
}

STYLE = (
    f"Impulse Learning Center visual style: deep navy {COLORS['background_card']} base, electric blue light "
    f"{COLORS['brand_light']} to {COLORS['brand_dark']}, light blue glow {COLORS['brand_glow']}, gold {COLORS['award_gold']} "
    "only for awards. Cinematic, premium, high contrast, photorealistic 3D, clean professional Instagram look."
)
NO_TEXT = (
    "This is a background artwork only: texts, logo, icons and contacts are added later as separate layers. "
    "Absolutely no text, letters, numbers, logos, icons, badges, buttons, frames or UI elements anywhere in the image."
)


def nearest_format(width: int, height: int) -> str:
    ratio = height / width
    return min(FORMATS, key=lambda f: abs(FORMATS[f]["size"][1] / FORMATS[f]["size"][0] - ratio))


def _asset_lines(assets: list[dict], first_index: int) -> list[str]:
    return [f"Reference image {i}: {a['role']}." for i, a in enumerate(assets, start=first_index)]


def keep_clear_phrase(spec: dict) -> str:
    """Where the Figma texts go: from spec.art.keep_clear, else from the reference's text boxes."""
    art = spec.get("art", {})
    if art.get("keep_clear"):
        return art["keep_clear"]
    w, h = FORMATS[spec["base"]]["size"]
    # Only the big text blocks matter (title, subtitle); small ones (logo, phone) fit anywhere
    boxes = [b for b in (spec.get("parity") or {}).get("text_boxes") or [] if b[2] * b[3] > 0.02 * w * h]
    if not boxes:
        return ""
    zones = "; ".join(f"x {b[0] / w:.0%}-{(b[0] + b[2]) / w:.0%}, y {b[1] / h:.0%}-{(b[1] + b[3]) / h:.0%}" for b in boxes)
    return f"Keep these areas as calm, darker and low in detail as in reference image 1, the texts go there later: {zones}."


def art_scenes(spec: dict, clean_plate: Path | None, change: str | None = None, variants: int = 1) -> tuple[list[dict], list[dict]]:
    """Flow scenes + import targets for the spec's artwork images (art, and art_<fmt> for extra formats)."""
    art = spec["art"]
    assets = [a for a in spec.get("source", {}).get("assets", []) if a.get("flow", True)]
    scenes, targets = [], []

    def scene(prompt: str, aspect: str, refs: list[str], previous: bool = False) -> dict:
        s = {"type": "image", "prompt": prompt, "aspect_ratio": aspect, "model": FLOW["poster_model"],
             "download_quality": FLOW["download_quality"]}
        if refs:
            s["reference_images"] = [str((ROOT / r).resolve()) if not Path(r).is_absolute() else r for r in refs][:3]
        if previous:
            s["reference_previous"] = True
        if variants > 1:
            s["variants"] = variants
        return s

    if change:
        for name in art_images(spec):
            current = spec["images"][name]["file"]
            prompt = (f"Edit reference image 1: {change}. Keep the composition, framing, subject, lighting, colours and "
                      f"everything else exactly the same. {NO_TEXT}")
            scenes.append(scene(prompt, art_aspect(spec, name), [current]))
            targets.append({"scene": len(scenes), "kind": "poster_art", "poster_id": spec["poster_id"], "image": name})
        return scenes, targets

    keep_clear = keep_clear_phrase(spec)
    replace = " ".join(art.get("replace", []))
    if spec["mode"] == "reference":
        refs = [str(clean_plate), *(a["file"] for a in assets)]
        prompt = " ".join(p for p in [
            "Recreate reference image 1 as a finished background artwork with 100% visual parity: identical composition "
            "and framing, camera angle and lens, subject placement and scale, lighting direction and intensity, colour "
            "palette, contrast, grain and mood.",
            *_asset_lines(assets, 2),
            f"Scene: {art['description']}",
            replace,
            "Areas that were cleaned out in reference image 1 continue the surrounding background naturally.",
            keep_clear, NO_TEXT,
        ] if p)
    else:
        refs = [a["file"] for a in assets]
        prompt = " ".join(p for p in [
            f"Background artwork for an Instagram {spec['poster_type']} poster. {art['description']}",
            *_asset_lines(assets, 1), replace, STYLE, keep_clear, NO_TEXT,
        ] if p)
    scenes.append(scene(prompt, art_aspect(spec, "art"), refs))
    targets.append({"scene": 1, "kind": "poster_art", "poster_id": spec["poster_id"], "image": "art"})

    # Other formats with their own artwork (art_story, ...): the same scene extended, from the previous image
    for name in art_images(spec)[1:]:
        fmt = name.split("_", 1)[1]
        prompt = (f"Extend the previous image to a {FORMATS[fmt]['flow_aspect']} frame: the same artwork, subject at the "
                  "same size relative to the frame width, more of the same background above and below. Nothing new is "
                  f"added. {NO_TEXT}")
        scenes.append(scene(prompt, FORMATS[fmt]["flow_aspect"], [], previous=True))
        targets.append({"scene": len(scenes), "kind": "poster_art", "poster_id": spec["poster_id"], "image": name})
    return scenes, targets


def art_images(spec: dict) -> list[str]:
    """Artwork image names in generation order: 'art' first, then 'art_<fmt>' that the formats use."""
    names = ["art"]
    for fmt, conf in spec.get("formats", {}).items():
        image = conf.get("overrides", {}).get("art", {}).get("image")
        if image and image not in names:
            names.append(image)
    return names


def art_aspect(spec: dict, name: str) -> str:
    if name != "art":
        return FORMATS[name.split("_", 1)[1]]["flow_aspect"]
    return spec["art"].get("aspect") or FORMATS[spec["base"]]["flow_aspect"]
