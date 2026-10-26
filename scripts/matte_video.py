"""
Video background removal (person matting) with Robust Video Matting (RVM, MobileNetV3, ONNX, CPU).

The person is cut out with a temporally stable alpha (RVM's recurrent state carries over between frames, so
edges do not flicker) and written as WebM VP9 with alpha (yuva420p) + the original audio. Remotion then puts the
cut-out on any background (studio, gradient, Flow artwork).

Model: assets/models/rvm_mobilenetv3_fp32.onnx
       (https://github.com/PeterL1n/RobustVideoMatting/releases/tag/v1.0.0, GPL-3.0)

Usage:
  python scripts/matte_video.py workspace/01_raw/reel_upgrade.mp4            # -> workspace/01_raw/reel_upgrade_matte.webm
  python scripts/matte_video.py in.mp4 --seconds 3 --preview                  # quick test: first 3 s + preview PNG
  python scripts/matte_video.py in.mp4 --grade                               # + shadows lifted, colour cast removed
  python scripts/matte_video.py in.mp4 --crop-bottom 0.36                     # erase everything below 64% height (desk)
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "assets/models/rvm_mobilenetv3_fp32.onnx"
# Default grade: lift shadows (gamma), a touch of contrast, pull red bounce light from a coloured wall out of the skin
GRADE = "eq=gamma=1.10:contrast=1.05,colorbalance=rs=-0.05:rm=-0.03:bs=0.03:bm=0.02"


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:stream_side_data=rotation:format=duration",
                          "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    s = info["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    w, h = int(s["width"]), int(s["height"])
    # Phone videos: stored landscape + display rotation; ffmpeg decodes them already rotated
    rotation = next((int(d.get("rotation", 0)) for d in s.get("side_data_list", []) if "rotation" in d), 0)
    if abs(rotation) % 180 == 90:
        w, h = h, w
    return {"w": w, "h": h, "fps": float(num) / float(den), "duration": float(info["format"]["duration"])}


def matte(src: Path, dest: Path, downsample: float, seconds: float | None, crop_bottom: float, preview: bool,
          grade: str | None = None, despill: bool = True) -> Path:
    info = probe(src)
    w, h, fps = info["w"], info["h"], info["fps"]
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    sess = ort.InferenceSession(str(MODEL), opts, providers=["CPUExecutionProvider"])

    limit = ["-t", str(seconds)] if seconds else []
    vf = ["-vf", grade] if grade else []
    reader = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), *limit, *vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                              stdout=subprocess.PIPE)
    dest.parent.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
        *limit, "-i", str(src), "-map", "0:v", "-map", "1:a?",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "22",
        "-deadline", "good", "-cpu-used", "4", "-row-mt", "1",
        "-c:a", "libopus", "-b:a", "128k", "-shortest", str(dest),
    ], stdin=subprocess.PIPE)

    rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    ratio = np.array([downsample], np.float32)
    keep = np.ones((h, 1), np.float32)
    if crop_bottom:
        # Soft cut-off for objects in front of the person (desk): fades out over 24 px
        edge = int(h * (1 - crop_bottom))
        keep = np.clip((edge - np.arange(h)) / 24.0, 0, 1).astype(np.float32)[:, None]

    bg_channel = None
    frame_bytes = w * h * 3
    n, started = 0, time.time()
    total = int((seconds or info["duration"]) * fps)
    while True:
        buf = reader.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        src_t = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        fgr, pha, *rec = sess.run(None, {"src": src_t, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                         "downsample_ratio": ratio})
        alpha = pha[0, 0] * keep
        fg_f = fgr[0].transpose(1, 2, 0)
        if despill:
            if bg_channel is None:
                bg_channel = background_channel(rgb, alpha)
            fg_f, alpha = despill_edges(fg_f, alpha, bg_channel)
        fg = (fg_f * 255).clip(0, 255).astype(np.uint8)
        rgba = np.dstack([fg, (alpha * 255).clip(0, 255).astype(np.uint8)])
        writer.stdin.write(rgba.tobytes())
        if preview and n in (0, int(fps * (seconds or 3) / 2)):
            _preview(rgba, dest.with_name(f"{dest.stem}_preview_{n}.png"))
        n += 1
        if n % 150 == 0:
            el = time.time() - started
            print(f"[matte] {n}/{total} kadr — {n / el:.1f} fps, ~{(total - n) / (n / el) / 60:.1f} min qoldi", flush=True)
    writer.stdin.close()
    writer.wait()
    reader.wait()
    print(f"[matte] {n} kadr, {time.time() - started:.0f} s -> {dest.resolve().relative_to(ROOT.resolve()).as_posix()}")
    return dest


def background_channel(rgb: np.ndarray, alpha: np.ndarray) -> int | None:
    """Dominant channel of a coloured wall/screen behind the person (red wall -> 0), None for a neutral background."""
    bg = rgb[alpha < 0.05]
    if len(bg) < 1000:
        return None
    mean = bg.reshape(-1, 3).mean(axis=0)
    ch = int(np.argmax(mean))
    others = np.delete(mean, ch)
    return ch if mean[ch] > others.max() * 1.25 else None


def despill_edges(fg: np.ndarray, alpha: np.ndarray, ch: int | None, band_px: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """Removes the coloured fringe a wall/screen leaves on hair and clothing edges.
    In a band around the edge the wall's channel is clamped to the brightest other channel; the alpha is choked by 1 px."""
    alpha = cv2.erode(alpha, np.ones((3, 3), np.uint8))
    if ch is None:
        return fg, alpha
    edge = ((alpha > 0.02) & (alpha < 0.98)).astype(np.uint8)
    band = cv2.dilate(edge, np.ones((band_px * 2 + 1, band_px * 2 + 1), np.uint8)).astype(bool)
    others = np.delete(fg, ch, axis=2).max(axis=2)
    fg = fg.copy()
    spill = fg[..., ch]
    # Skin is naturally ~1.3x red: only clearly wall-coloured pixels (fringe) are pulled back
    fg[..., ch] = np.where(band, np.minimum(spill, others * 1.4 + 0.03), spill)
    return fg, alpha


def _preview(rgba: np.ndarray, out: Path) -> None:
    """Cut-out on a checkerboard + on navy, side by side — edges and holes are easy to judge."""
    img = Image.fromarray(rgba, "RGBA")
    w, h = img.size
    checker = Image.new("RGB", (w, h), (200, 200, 200))
    tile = Image.new("RGB", (24, 24), (150, 150, 150))
    for y in range(0, h, 48):
        for x in range(0, w, 48):
            checker.paste(tile, (x, y))
            checker.paste(tile, (x + 24, y + 24))
    navy = Image.new("RGB", (w, h), (10, 22, 49))
    sheet = Image.new("RGB", (w * 2, h))
    for i, bg in enumerate((checker, navy)):
        bg.paste(img, (0, 0), img)
        sheet.paste(bg, (i * w, 0))
    sheet.save(out)


def main() -> None:
    p = argparse.ArgumentParser(description="RVM person matting -> WebM with alpha")
    p.add_argument("input")
    p.add_argument("--out")
    p.add_argument("--downsample", type=float, default=0.375, help="RVM downsample_ratio (720x1280: 0.375)")
    p.add_argument("--seconds", type=float, help="Faqat boshidagi N soniya (test)")
    p.add_argument("--crop-bottom", type=float, default=0.0, help="Pastki ulushni olib tashlash (stol), 0..1")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--no-despill", action="store_true", help="Rangli devor aksini chetlardan olib tashlamaslik")
    p.add_argument("--grade", nargs="?", const=GRADE, help="Rang tuzatish (ffmpeg -vf). Bayroq o'zi: soyalarni ko'tarish + qizil devor aksini kamaytirish")
    a = p.parse_args()
    src = Path(a.input)
    dest = Path(a.out) if a.out else src.with_name(f"{src.stem}_matte.webm")
    matte(src, dest, a.downsample, a.seconds, a.crop_bottom, a.preview, a.grade, not a.no_despill)


if __name__ == "__main__":
    main()
