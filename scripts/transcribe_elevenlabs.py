"""
ElevenLabs Scribe (speech-to-text) orqali o'zbek + ingliz aralash nutqni so'zma-so'z vaqt belgilari bilan yozib olish.

Natija: workspace/02_transcripts/<nom>.json (words + segments) va <nom>.srt (Scribe eksporti)
Subtitrlar Remotion'da shu .json dan chiziladi (scripts/build_captions.py).

Ishlatish:
  python scripts/transcribe_elevenlabs.py workspace/01_raw/speaking_part2_cut.mp4
  python scripts/transcribe_elevenlabs.py workspace/01_raw/speaking_part2_cut.mp4 \
      --plan workspace/03_edit_plans/speaking_part2.json --keyterm "over the moon" --language uzb
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BRAND = json.loads((ROOT / "config/brand_preset.json").read_text(encoding="utf-8"))
EL = BRAND["ai_generation"]["elevenlabs"]
TRANSCRIPTS_DIR = ROOT / "workspace/02_transcripts"
API_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# Scribe'ni IELTS atamalarini to'g'ri yozishga yo'naltiradi (keyterms +20% narx)
DEFAULT_KEYTERMS = [
    "IELTS", "Band 8.0", "Band Descriptor", "Task Response", "Task Achievement", "Lexical Resource",
    "Coherence and Cohesion", "Grammatical Range", "Fluency", "Speaking Part 2", "Writing Task 2",
    "collocation", "idiom", "paraphrase", "Mock Exam",
]


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    return p.relative_to(ROOT.resolve()).as_posix() if p.is_relative_to(ROOT.resolve()) else p.as_posix()


def extract_audio(video_path: Path, tmp_dir: Path) -> Path:
    out = tmp_dir / "audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(out)],
        check=True,
    )
    return out


def collect_keyterms(plan_path: Path | None, extra: list[str]) -> list[str]:
    terms = list(DEFAULT_KEYTERMS) + extra
    if plan_path and plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        for items in plan.get("keywords", {}).values():
            terms.extend(items)
    seen, result = set(), []
    for t in terms:
        t = t.strip()
        # API cheklovi: < 50 belgi, ≤ 5 so'z, maxsus belgilarsiz
        if t and t.lower() not in seen and len(t) < 50 and len(t.split()) <= 5 and not set(t) & set("<>{}[]\\"):
            seen.add(t.lower())
            result.append(t)
    return result[:100]  # 100 tadan oshsa minimal 20s billing qo'llanadi


def scribe(audio_path: Path, keyterms: list[str], language: str | None) -> dict:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("ELEVENLABS_API_KEY .env faylida topilmadi")
    data = {
        "model_id": EL["stt_model"],
        "timestamps_granularity": "word",
        "tag_audio_events": "false",
        "diarize": "true",  # additional_formats (srt) talab qiladi
        "keyterms": keyterms,
    }
    if language:
        data["language_code"] = language
    with open(audio_path, "rb") as f:
        files = {
            "file": (audio_path.name, f, "audio/mpeg"),
            "additional_formats": (None, json.dumps([{"format": "srt", "max_characters_per_line": 32}]), "application/json"),
        }
        with httpx.Client(timeout=900) as http:
            resp = http.post(API_URL, headers={"xi-api-key": api_key}, data=data, files=files)
    if resp.status_code != 200:
        sys.exit(f"ElevenLabs STT xatosi {resp.status_code}: {resp.text[:800]}")
    return resp.json()


def to_segments(words: list[dict], max_gap: float = 0.6, max_len: float = 6.0) -> list[dict]:
    segments, current = [], []
    for w in words:
        if current and (w["start"] - current[-1]["end"] > max_gap or w["end"] - current[0]["start"] > max_len):
            segments.append(current)
            current = []
        current.append(w)
    if current:
        segments.append(current)
    return [{"start": s[0]["start"], "end": s[-1]["end"], "text": " ".join(w["word"] for w in s)} for s in segments]


def transcribe(video_path: Path, plan_path: Path | None = None, extra_keyterms: list[str] | None = None,
               language: str | None = None) -> Path:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    keyterms = collect_keyterms(plan_path, extra_keyterms or [])
    with tempfile.TemporaryDirectory() as tmp:
        result = scribe(extract_audio(video_path, Path(tmp)), keyterms, language or EL.get("stt_language"))

    words = [
        {"word": w["text"].strip(), "start": w["start"], "end": w["end"]}
        for w in result.get("words", []) if w.get("type") == "word" and w["text"].strip()
    ]
    transcript = {
        "source": _rel(video_path),
        "model": EL["stt_model"],
        "language": result.get("language_code"),
        "language_probability": result.get("language_probability"),
        "text": result.get("text", ""),
        "duration": result.get("audio_duration_secs") or (words[-1]["end"] if words else 0),
        "keyterms": keyterms,
        "segments": to_segments(words),
        "words": words,
    }
    json_path = TRANSCRIPTS_DIR / f"{video_path.stem}.json"
    json_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8")

    for fmt in result.get("additional_formats") or []:
        if fmt and fmt.get("requested_format") == "srt" and not fmt.get("is_base64_encoded"):
            (TRANSCRIPTS_DIR / f"{video_path.stem}.srt").write_text(fmt["content"], encoding="utf-8")

    print(f"[scribe] {_rel(json_path)} — {len(words)} so'z, til: {transcript['language']}")
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="ElevenLabs Scribe transkripsiya (o'zbek + ingliz)")
    parser.add_argument("input", help="Video yoki audio fayl")
    parser.add_argument("--plan", help="edit_plan.json — keywords keyterm sifatida qo'shiladi")
    parser.add_argument("--keyterm", action="append", default=[], help="Qo'shimcha atama (bir necha marta)")
    parser.add_argument("--language", help="ISO kod (uzb, eng). Bo'sh qoldirilsa avtomatik aniqlanadi")
    args = parser.parse_args()

    resolve = lambda p: Path(p) if Path(p).is_absolute() else ROOT / p
    transcribe(resolve(args.input), resolve(args.plan) if args.plan else None, args.keyterm, args.language)


if __name__ == "__main__":
    main()
