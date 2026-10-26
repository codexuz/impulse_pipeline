"""
ElevenLabs API orqali SFX, ambient BGM, Band 9.0 Native TTS va shovqindan tozalash (Audio Isolation).

Ishlatish:
  python scripts/generate_elevenlabs_audio.py sfx --name pop_idiom --prompt "soft bubbly pop, short UI accent" --duration 1
  python scripts/generate_elevenlabs_audio.py bgm --name lofi_loop --prompt "warm lo-fi study beat, mellow keys, no vocals"
  python scripts/generate_elevenlabs_audio.py tts --name over_the_moon_uk --text "I was over the moon." --accent british
  python scripts/generate_elevenlabs_audio.py isolate --input workspace/01_raw/speaking_part2.mp4
  python scripts/generate_elevenlabs_audio.py --from-plan workspace/03_edit_plans/speaking_idioms.json
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
EL_SETTINGS = BRAND["ai_generation"]["elevenlabs"]
AI_DIR = ROOT / "assets/ai_generated"
API_BASE = "https://api.elevenlabs.io/v1"

VOICES = {
    "british": os.getenv("ELEVENLABS_VOICE_BRITISH", "JBFqnCBsd6RMkjVDRZzb"),
    "american": os.getenv("ELEVENLABS_VOICE_AMERICAN", "21m00Tcm4TlvDq8ikWAM"),
}


def _headers() -> dict:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("ELEVENLABS_API_KEY .env faylida topilmadi")
    return {"xi-api-key": api_key}


def _rel(path: Path) -> str:
    p = path.resolve()
    return p.relative_to(ROOT.resolve()).as_posix() if p.is_relative_to(ROOT.resolve()) else p.as_posix()


def _post_audio(endpoint: str, out_path: Path, **request_kwargs) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=300) as http:
        resp = http.post(f"{API_BASE}{endpoint}", headers=_headers(), **request_kwargs)
    if resp.status_code != 200:
        sys.exit(f"ElevenLabs xatosi {resp.status_code}: {resp.text[:500]}")
    out_path.write_bytes(resp.content)
    print(f"[yaratildi] {_rel(out_path)}")
    return out_path


def generate_sfx(prompt: str, name: str, duration: float | None = None, folder: str = "sfx", force: bool = False) -> Path:
    """POST /v1/sound-generation — qisqa SFX yoki ambient fon (BGM loop)."""
    out_path = AI_DIR / folder / f"{name}.mp3"
    if out_path.exists() and not force:
        print(f"[kesh] {_rel(out_path)}")
        return out_path
    body = {"text": prompt, "prompt_influence": EL_SETTINGS["sfx_prompt_influence"]}
    if duration:
        body["duration_seconds"] = duration
    return _post_audio("/sound-generation", out_path, json=body)


def generate_bgm(prompt: str, name: str, duration: float | None = None, force: bool = False) -> Path:
    return generate_sfx(prompt, name, duration or EL_SETTINGS["bgm_default_duration_sec"], folder="bgm", force=force)


def generate_tts(text: str, name: str, accent: str = "british", force: bool = False) -> Path:
    """POST /v1/text-to-speech/{voice_id} — Band 9.0 Native Speaker talaffuz namunasi."""
    out_path = AI_DIR / "voiceovers" / f"{name}.mp3"
    if out_path.exists() and not force:
        print(f"[kesh] {_rel(out_path)}")
        return out_path
    voice_id = VOICES.get(accent, accent)  # accent o'rniga to'g'ridan-to'g'ri voice_id ham berish mumkin
    return _post_audio(
        f"/text-to-speech/{voice_id}",
        out_path,
        params={"output_format": "mp3_44100_128"},
        json={
            "text": text,
            "model_id": EL_SETTINGS["tts_model"],
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.15},
        },
    )


def isolate_voice(input_path: Path) -> Path:
    """
    POST /v1/audio-isolation — shovqinli xonada/ko'chada yozilgan ovozni studiya darajasida tozalaydi.
    Natija: workspace/01_raw/<nom>_clean.wav
    """
    out_path = input_path.with_name(f"{input_path.stem}_clean.wav")
    with tempfile.TemporaryDirectory() as tmp:
        src_audio = Path(tmp) / "source.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path), "-vn", "-ac", "1", "-ar", "44100", str(src_audio)],
            check=True,
        )
        isolated = Path(tmp) / "isolated.mp3"
        with open(src_audio, "rb") as f:
            _post_audio("/audio-isolation", isolated, files={"audio": ("source.wav", f, "audio/wav")})
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(isolated), "-ar", "48000", str(out_path)],
            check=True,
        )
    print(f"[tozalandi] {_rel(out_path)}")
    return out_path


def generate_from_plan(plan_path: Path, force: bool = False) -> None:
    """edit_plan.json dagi "audio" bo'limi: sfx[], bgm{}, voiceovers[] — fayllarni yaratib, yo'lini yozadi."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    audio = plan.get("audio", {})

    for item in audio.get("sfx", []):
        if item.get("prompt") and (force or not item.get("file")):
            item["file"] = _rel(generate_sfx(item["prompt"], item["id"], item.get("duration"), force=force))

    bgm = audio.get("bgm")
    if bgm and bgm.get("prompt") and (force or not bgm.get("file")):
        bgm["file"] = _rel(generate_bgm(bgm["prompt"], bgm["id"], bgm.get("duration"), force=force))

    for item in audio.get("voiceovers", []):
        if item.get("text") and (force or not item.get("file")):
            item["file"] = _rel(generate_tts(item["text"], item["id"], item.get("accent", "british"), force=force))

    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="ElevenLabs SFX / BGM / TTS / Audio Isolation")
    parser.add_argument("--from-plan", help="edit_plan.json — undagi barcha audio elementlarni yaratadi")
    parser.add_argument("--force", action="store_true", help="Keshdagi faylni qayta yaratish")
    sub = parser.add_subparsers(dest="command")

    for name in ("sfx", "bgm"):
        p = sub.add_parser(name)
        p.add_argument("--name", required=True)
        p.add_argument("--prompt", required=True)
        p.add_argument("--duration", type=float)

    t = sub.add_parser("tts")
    t.add_argument("--name", required=True)
    t.add_argument("--text", required=True)
    t.add_argument("--accent", default="british", help="british | american | <voice_id>")

    i = sub.add_parser("isolate")
    i.add_argument("--input", required=True)

    args = parser.parse_args()
    if args.from_plan:
        plan = Path(args.from_plan)
        generate_from_plan(plan if plan.is_absolute() else ROOT / plan, args.force)
    elif args.command == "sfx":
        generate_sfx(args.prompt, args.name, args.duration, force=args.force)
    elif args.command == "bgm":
        generate_bgm(args.prompt, args.name, args.duration, force=args.force)
    elif args.command == "tts":
        generate_tts(args.text, args.name, args.accent, force=args.force)
    elif args.command == "isolate":
        src = Path(args.input)
        isolate_voice(src if src.is_absolute() else ROOT / src)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
