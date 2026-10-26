"""
Pauza va duduqlanishlarni kesib tashlash (auto-cut) hamda ovozni -14 LUFS ga normalizatsiya qilish.

1. (ixtiyoriy) ElevenLabs Audio Isolation bilan ovozni tozalash
2. ffmpeg silencedetect bilan 0.35s dan uzun pauzalarni topish
3. Faqat gapirilgan qismlarni qoldirib, video + audioni birga kesish
4. loudnorm I=-14 (Instagram standarti)

Natija: workspace/01_raw/<nom>_cut.mp4

Ishlatish:
  python scripts/silence_remover.py workspace/01_raw/speaking_part2.mp4
  python scripts/silence_remover.py workspace/01_raw/speaking_part2.mp4 --isolate --min-silence 0.4 --noise -32
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    return p.relative_to(ROOT.resolve()).as_posix() if p.is_relative_to(ROOT.resolve()) else p.as_posix()


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def detect_silences(audio_source: Path, noise_db: float, min_silence: float) -> list[tuple[float, float]]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(audio_source), "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", proc.stderr)]
    if len(ends) < len(starts):  # video pauza bilan tugasa
        ends.append(float("inf"))
    return list(zip(starts, ends))


def keep_segments(silences: list[tuple[float, float]], duration: float, padding: float) -> list[tuple[float, float]]:
    """Pauzalar orasidagi gapirilgan qismlar; so'z oxiri kesilmasligi uchun har tomondan padding qoldiriladi."""
    segments, cursor = [], 0.0
    for start, end in silences:
        seg_end = min(duration, start + padding)
        if seg_end - cursor > 0.05:
            segments.append((cursor, seg_end))
        cursor = max(cursor, end - padding)
    if duration - cursor > 0.05:
        segments.append((cursor, duration))
    return segments


def cut_video(video: Path, audio: Path | None, segments: list[tuple[float, float]], out_path: Path) -> None:
    between = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in segments)
    audio_input = "1:a" if audio else "0:a"
    filter_graph = (
        f"[0:v]select='{between}',setpts=N/FRAME_RATE/TB[v];"
        f"[{audio_input}]aselect='{between}',asetpts=N/SR/TB,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(filter_graph)  # uzun videolarda filtr buyruq qatoriga sig'maydi
        script_path = f.name
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += [
        "-/filter_complex", script_path, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True)
    finally:
        Path(script_path).unlink(missing_ok=True)


def remove_silence(video: Path, isolate: bool, noise_db: float, min_silence: float, padding: float) -> Path:
    clean_audio = None
    if isolate:
        from generate_elevenlabs_audio import isolate_voice
        clean_audio = isolate_voice(video)

    duration = probe_duration(video)
    silences = detect_silences(clean_audio or video, noise_db, min_silence)
    segments = keep_segments(silences, duration, padding)
    out_path = video.with_name(f"{video.stem}_cut.mp4")
    cut_video(video, clean_audio, segments, out_path)

    kept = sum(b - a for a, b in segments)
    print(f"[auto-cut] {len(silences)} ta pauza kesildi: {duration:.1f}s -> {kept:.1f}s | {_rel(out_path)}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Pauzalarni kesish + -14 LUFS normalizatsiya")
    parser.add_argument("input")
    parser.add_argument("--isolate", action="store_true", help="Avval ElevenLabs Audio Isolation bilan tozalash")
    parser.add_argument("--noise", type=float, default=-35.0, help="Sukunat chegarasi, dB")
    parser.add_argument("--min-silence", type=float, default=0.35, help="Kesiladigan eng qisqa pauza, soniya")
    parser.add_argument("--padding", type=float, default=0.08, help="So'z atrofida qoldiriladigan zaxira, soniya")
    args = parser.parse_args()

    src = Path(args.input)
    remove_silence(src if src.is_absolute() else ROOT / src, args.isolate, args.noise, args.min_silence, args.padding)


if __name__ == "__main__":
    main()
