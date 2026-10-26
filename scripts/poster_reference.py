"""
Reference posters -> measurable design data for "100% parity" (scripts/poster_studio.py uses these).

  analyze  the reference is scaled to the design format (1080 px wide) and a pixel grid is drawn on it, so
           every coordinate read from the grid image is already a Figma coordinate; + dominant palette.
  measure  zoomed crops of chosen boxes with a fine 10 px grid + the text and background colour of each box
           (font size, letter spacing and colour are read from these).
  clean    the reference's texts/logo inpainted out (OpenCV Telea) -> reference image 1 for Flow, so Flow
           copies the scene but has no text to copy.
  compare  parity sheet: reference | Figma export | 50% overlay, plus layout and colour similarity scores.

Usage:
  python scripts/poster_reference.py analyze --image reference/example_edits/sample_posters/x.jpg --out workspace/05_posters/refs/x
  python scripts/poster_reference.py measure --image workspace/05_posters/refs/x/reference_design.png --box title=60,540,640,170
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from flow_design import FORMATS, nearest_format

ROOT = Path(__file__).resolve().parent.parent


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def to_design(image: Path, fmt: str | None = None) -> tuple[Image.Image, str]:
    """Scale the reference to the design format's width (and crop/pad to its height if the ratio differs slightly)."""
    img = Image.open(image).convert("RGB")
    fmt = fmt or nearest_format(*img.size)
    w, h = FORMATS[fmt]["size"]
    scaled = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
    if scaled.height != h:
        canvas = Image.new("RGB", (w, h), scaled.getpixel((w // 2, scaled.height - 1)))
        canvas.paste(scaled, (0, (h - scaled.height) // 2))
        scaled = canvas
    return scaled, fmt


def grid_overlay(img: Image.Image, step: int = 54, major: int = 108, label: bool = True) -> Image.Image:
    out = img.convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = _font(max(12, out.width // 70))
    for x in range(0, out.width, step):
        d.line([(x, 0), (x, out.height)], fill=(255, 64, 64, 150 if x % major == 0 else 60), width=1)
        if label and x % major == 0:
            d.text((x + 3, 3), str(x), fill=(255, 230, 0, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for y in range(0, out.height, step):
        d.line([(0, y), (out.width, y)], fill=(255, 64, 64, 150 if y % major == 0 else 60), width=1)
        if label and y % major == 0 and y:
            d.text((3, y + 3), str(y), fill=(255, 230, 0, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    return Image.alpha_composite(out, layer).convert("RGB")


def palette(img: Image.Image, colors: int = 8) -> list[dict]:
    q = img.resize((180, round(180 * img.height / img.width))).quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    return [{"hex": "#%02X%02X%02X" % tuple(pal[i * 3:i * 3 + 3]), "share": round(c / total, 3)} for c, i in counts]


def box_colors(img: Image.Image, box: list[int]) -> dict:
    """Two-cluster split of a text box: the larger cluster is the background, the smaller one the text colour."""
    x, y, w, h = box
    crop = np.asarray(img.crop((x, y, x + w, y + h))).reshape(-1, 3).astype(np.float32)
    if len(crop) < 4:
        return {}
    _, labels, centers = cv2.kmeans(crop, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3,
                                    cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=2)
    bg, fg = (0, 1) if counts[0] >= counts[1] else (1, 0)
    hexc = lambda c: "#%02X%02X%02X" % tuple(int(v) for v in np.clip(c, 0, 255))
    return {"text": hexc(centers[fg]), "background": hexc(centers[bg]), "text_share": round(float(counts[fg] / counts.sum()), 3)}


def analyze(image: Path, out_dir: Path, fmt: str | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    original = Image.open(image)
    design, fmt = to_design(image, fmt)
    design.save(out_dir / "reference_design.png")
    grid_overlay(design).save(out_dir / "reference_grid.png")
    info = {
        "reference": image.resolve().relative_to(ROOT.resolve()).as_posix() if image.resolve().is_relative_to(ROOT.resolve()) else str(image),
        "original_size": list(original.size),
        "base": fmt,
        "design_size": list(design.size),
        "scale": round(design.width / original.width, 4),
        "palette": palette(design),
        "files": {"design": (out_dir / "reference_design.png").as_posix(), "grid": (out_dir / "reference_grid.png").as_posix()},
    }
    (out_dir / "analysis.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def measure(image: Path, boxes: dict[str, list[int]], out: Path, zoom: int = 3) -> dict:
    """Zoomed crops with a 10 px grid (in design px) + colours, stacked in one sheet."""
    img = Image.open(image).convert("RGB")
    tiles, result = [], {}
    for name, (x, y, w, h) in boxes.items():
        crop = img.crop((x, y, x + w, y + h)).resize((w * zoom, h * zoom), Image.LANCZOS)
        tile = grid_overlay(crop, step=10 * zoom, major=50 * zoom, label=False)
        d = ImageDraw.Draw(tile)
        for gx in range(0, w, 50):
            d.text((gx * zoom + 2, 2), str(x + gx), fill=(255, 230, 0), font=_font(14), stroke_width=2, stroke_fill=(0, 0, 0))
        for gy in range(0, h, 50):
            d.text((2, gy * zoom + 2), str(y + gy), fill=(255, 230, 0), font=_font(14), stroke_width=2, stroke_fill=(0, 0, 0))
        result[name] = {"box": [x, y, w, h], **box_colors(img, [x, y, w, h])}
        header = Image.new("RGB", (tile.width, 28), (20, 20, 20))
        ImageDraw.Draw(header).text((6, 5), f"{name} {x},{y},{w},{h}  text {result[name].get('text')}  bg {result[name].get('background')}",
                                    fill=(255, 255, 255), font=_font(16))
        tiles.append(header)
        tiles.append(tile)
    sheet = Image.new("RGB", (max(t.width for t in tiles), sum(t.height for t in tiles)), (0, 0, 0))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y))
        y += t.height
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return result


def clean_plate(design_image: Path, boxes: list[list[int]], out: Path, pad: int = 10) -> Path:
    """Inpaint text/logo boxes (design px) out of the reference: Flow gets the scene without any text."""
    img = cv2.imread(str(design_image))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Only the letter strokes are masked (pixels that stand out from the local median background),
    # so the scene behind the text (trophy base, ground) survives; whole boxes would leave smeared blocks.
    local_bg = cv2.medianBlur(gray, 31)
    strokes = (cv2.absdiff(gray, local_bg) > 28).astype(np.uint8) * 255
    mask = np.zeros(img.shape[:2], np.uint8)
    for x, y, w, h in boxes:
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), x + w + pad, y + h + pad
        mask[y0:y1, x0:x1] = strokes[y0:y1, x0:x1]
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    radius = 7
    cleaned = cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)
    # Smooth the filled areas a little so no letter ghosts stay
    blurred = cv2.GaussianBlur(cleaned, (0, 0), 6)
    soft = cv2.GaussianBlur(mask, (0, 0), 4).astype(np.float32)[..., None] / 255.0
    result = (cleaned * (1 - soft) + blurred * soft).astype(np.uint8)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), result)
    return out


def compare(reference_design: Path, export: Path, out: Path) -> dict:
    """Parity sheet + scores (0-100). Different texts lower the score a little; layout and colour should stay high."""
    exp = Image.open(export).convert("RGB")
    ref = Image.open(reference_design).convert("RGB")
    if ref.size != exp.size:
        ref, _ = to_design(reference_design, nearest_format(*exp.size))
        ref = ref.resize(exp.size, Image.LANCZOS)

    def small(im: Image.Image) -> np.ndarray:
        return cv2.cvtColor(np.asarray(im.resize((54, round(54 * im.height / im.width)), Image.BOX)), cv2.COLOR_RGB2LAB).astype(np.float32)

    color = max(0.0, 100 - float(np.abs(small(ref) - small(exp)).mean()) * 2)

    def edges(im: Image.Image) -> np.ndarray:
        g = cv2.cvtColor(np.asarray(im.resize((270, round(270 * im.height / im.width)))), cv2.COLOR_RGB2GRAY)
        return cv2.GaussianBlur(cv2.Canny(g, 60, 160).astype(np.float32), (0, 0), 6).flatten()

    e1, e2 = edges(ref), edges(exp)
    layout = float(np.corrcoef(e1, e2)[0, 1] * 100) if e1.std() and e2.std() else 0.0

    w = 540
    tiles = [im.resize((w, round(w * im.height / im.width)), Image.LANCZOS) for im in (ref, exp, Image.blend(ref, exp, 0.5))]
    sheet = Image.new("RGB", (w * 3 + 40, tiles[0].height + 36), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    for i, (t, label) in enumerate(zip(tiles, ("reference", "figma export", "overlay 50%"))):
        sheet.paste(t, (i * (w + 20), 36))
        d.text((i * (w + 20) + 6, 8), label, fill=(255, 255, 255), font=_font(18))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {"color": round(color, 1), "layout": round(layout, 1), "sheet": out.as_posix()}


def _boxes(items: list[str]) -> dict[str, list[int]]:
    out = {}
    for i, item in enumerate(items):
        name, _, nums = item.rpartition("=")
        out[name or f"box{i + 1}"] = [int(float(v)) for v in nums.split(",")]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Reference poster analysis")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--image", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--format", choices=list(FORMATS))
    m = sub.add_parser("measure")
    m.add_argument("--image", required=True, help="reference_design.png (design px)")
    m.add_argument("--box", action="append", required=True, help="name=x,y,w,h in design px")
    m.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--reference", required=True)
    c.add_argument("--export", required=True)
    c.add_argument("--out", required=True)
    args = p.parse_args()
    if args.command == "analyze":
        print(json.dumps(analyze(Path(args.image), Path(args.out), args.format), indent=2))
    elif args.command == "measure":
        print(json.dumps(measure(Path(args.image), _boxes(args.box), Path(args.out)), indent=2))
    else:
        print(json.dumps(compare(Path(args.reference), Path(args.export), Path(args.out)), indent=2))


if __name__ == "__main__":
    main()
