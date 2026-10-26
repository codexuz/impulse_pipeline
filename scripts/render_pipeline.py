"""
Instagram Reels pipeline: xom video -> auto-cut -> ElevenLabs Scribe -> edit_plan.json -> Remotion render.

Bosqichlar:
  prepare — pauzalarni kesish (silence_remover, ixtiyoriy ElevenLabs Audio Isolation) va Scribe transkripsiya.
            Shundan so'ng Claude Code reference/prompts/transcript_analyzer.md bo'yicha edit_plan.json tuzadi.
  assets  — Flow uchun so'rov (flow_assets.py request) + ElevenLabs SFX/BGM/TTS. Flow'ni Claude MCP orqali ishga tushiradi.
  render  — subtitr sahifalari, Fluent emojilar, fayllarni remotion/public ga joylash va `Reel` kompozitsiyasini render.
            Reels muqovasi Remotion'da emas — `assets` bosqichida Google Flow'da (sarlavha matni bilan) yaratiladi.

Ishlatish:
  python scripts/render_pipeline.py prepare workspace/01_raw/speaking_part2_idioms.mp4 --isolate
  python scripts/render_pipeline.py assets workspace/03_edit_plans/speaking_part2_idioms.json
  python scripts/render_pipeline.py render workspace/03_edit_plans/speaking_part2_idioms.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_captions import build_pages  # noqa: E402
from fluent_emoji import fetch as fetch_emoji  # noqa: E402
from remotion_utils import BRAND, ROOT, Stage, rel, render_video, resolve  # noqa: E402

VIDEO = BRAND["video_settings"]
LOGO = BRAND["brand"]["logo_full"]
EXPORTS_DIR = ROOT / "workspace/04_exports"
TRANSCRIPTS_DIR = ROOT / "workspace/02_transcripts"


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def db_to_gain(db: float) -> float:
    return round(10 ** (db / 20), 4)


# ---------------------------------------------------------------------------
# prepare / assets
# ---------------------------------------------------------------------------

def prepare(raw_video: Path, isolate: bool, language: str | None) -> None:
    from silence_remover import remove_silence
    from transcribe_elevenlabs import transcribe

    cut = remove_silence(raw_video, isolate=isolate, noise_db=-35.0, min_silence=0.35, padding=0.08)
    transcript = transcribe(cut, language=language)
    print(
        "\nKeyingi qadam: transkripsiyani tahlil qilib edit_plan.json tuzing\n"
        f"  manba:         {rel(cut)}\n"
        f"  transkripsiya: {rel(transcript)}\n"
        f"  reja:          workspace/03_edit_plans/{raw_video.stem}.json  (sxema: reference/prompts/transcript_analyzer.md)"
    )


def assets(plan_path: Path) -> None:
    from flow_assets import request_for_plan
    from generate_elevenlabs_audio import generate_from_plan as gen_audio

    gen_audio(plan_path)
    try:
        request_for_plan(plan_path)
        print("\nClaude: yuqoridagi argumentlar bilan mcp__flow__flow_generate -> flow_wait, keyin:\n"
              "  python scripts/flow_assets.py import workspace/flow_requests/<so'rov>.json")
    except SystemExit as e:
        print(e)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _emoji(stage: Stage, name: str | None) -> str:
    if not name:
        return ""
    try:
        return stage.add(fetch_emoji(name))
    except KeyError as e:
        print(f"[ogohlantirish] {e}")
        return ""


def _transcript_for(plan: dict) -> Path | None:
    if plan.get("transcript"):
        return resolve(plan["transcript"])
    guess = TRANSCRIPTS_DIR / f"{resolve(plan['source']).stem}.json"
    return guess if guess.exists() else None


def _card(c: dict) -> dict:
    base = {"type": c["type"], "start": c["start"], "end": c["end"]}
    if c["type"] == "compare":
        return {**base, "weak": c["weak"], "strong": c["strong"],
                "weakLabel": c.get("weak_label", "BAND 5.5"), "strongLabel": c.get("strong_label", "BAND 8.0")}
    if c["type"] == "band_meter":
        return {**base, "from": float(c["from"]), "to": float(c["to"]), "label": c.get("label", "Overall Band")}
    return {**base, "icon": c.get("icon", "Sparkles"), "text": c["text"], "tone": c.get("tone", "brand")}


def build_reel_props(plan: dict, stage: Stage) -> dict:
    source = resolve(plan["source"])
    duration = plan.get("duration") or probe_duration(source)

    transcript = _transcript_for(plan)
    pages = []
    if transcript and transcript.exists():
        words = json.loads(transcript.read_text(encoding="utf-8"))["words"]
        pages = build_pages(words, plan.get("keywords", {}))
    else:
        print("[ogohlantirish] transkripsiya topilmadi — subtitrsiz render")

    missing = [v["id"] for v in plan.get("visuals", []) if not v.get("file") or not resolve(v["file"]).exists()]
    if missing:
        print(f"[ogohlantirish] fayli yo'q vizuallar o'tkazib yuboriladi: {missing} (render_pipeline.py assets)")

    hook, cta = plan.get("hook"), plan.get("cta")
    audio = plan.get("audio", {})
    bgm = audio.get("bgm")

    def staged_audio(items: list[dict], default_db: float) -> list[dict]:
        out = []
        for item in items:
            src = stage.add(item.get("file")) if item.get("file") else ""
            if src:
                out.append({"src": src, "at": float(item["at"]), "volume": db_to_gain(item.get("volume_db", default_db))})
        return out

    return {
        "fps": VIDEO["fps"],
        "durationInSeconds": round(duration, 3),
        "source": stage.add(source, f"source{source.suffix}"),
        "logo": stage.add(plan.get("logo", LOGO)) if plan.get("watermark", True) else "",
        "voiceVolume": audio.get("voice_volume", 1.0),
        "hook": {"text": hook["text"], "emoji": _emoji(stage, hook.get("emoji")),
                 "start": hook.get("start", 0), "end": hook.get("end", 2.5)} if hook and hook.get("text") else None,
        "captionPages": pages,
        "zooms": [{"start": z["start"], "end": z["end"], "scale": z.get("scale", 1.12)} for z in plan.get("zooms", [])],
        "visuals": [
            {"id": v["id"], "kind": v.get("kind", "broll"), "src": stage.add(v["file"]),
             "position": v.get("position", "top"), "start": v["start"], "end": v["end"]}
            for v in plan.get("visuals", []) if v["id"] not in missing
        ],
        "emojis": [
            {"src": src, "position": e.get("position", "top"), "size": e.get("size", 320), "start": e["start"], "end": e["end"]}
            for e in plan.get("emojis", []) if (src := _emoji(stage, e.get("name")))
        ],
        "cards": [_card(c) for c in plan.get("cards", [])],
        "cta": {"text": cta["text"], "icon": cta.get("icon", "MessageCircle"),
                "emoji": _emoji(stage, cta.get("emoji", "backhand index pointing down")),
                "start": cta.get("start", max(0, duration - 3))} if cta and cta.get("text") else None,
        "bgm": {"src": stage.add(bgm["file"]),
                "volume": db_to_gain(bgm["volume_db"]) if "volume_db" in bgm else VIDEO["bgm_volume"],
                "duckVolume": VIDEO["bgm_duck_volume"], "ducking": bgm.get("ducking", True)}
        if bgm and bgm.get("file") and resolve(bgm["file"]).exists() else None,
        "sfx": staged_audio(audio.get("sfx", []), -6),
        "voiceovers": staged_audio(audio.get("voiceovers", []), 0),
    }


def render(plan_path: Path) -> Path:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan.setdefault("id", plan_path.stem)
    stage = Stage(f"reel_{plan['id']}")
    out_path = resolve(plan.get("output") or f"workspace/04_exports/{plan['id']}.mp4")
    try:
        props_path = stage.write_props(build_reel_props(plan, stage))
        render_video("Reel", props_path, out_path)
    finally:
        stage.cleanup()
    print(f"[render] {rel(out_path)}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram Reels pipeline (ElevenLabs + Google Flow + Remotion)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="Auto-cut + ElevenLabs Scribe transkripsiya")
    p.add_argument("input")
    p.add_argument("--isolate", action="store_true", help="ElevenLabs Audio Isolation bilan tozalash")
    p.add_argument("--language", help="ISO kod (uzb, eng). Bo'sh — avtomatik")

    a = sub.add_parser("assets", help="ElevenLabs audio + Flow so'rovi")
    a.add_argument("plan")

    r = sub.add_parser("render", help="edit_plan.json asosida Remotion render")
    r.add_argument("plan")

    args = parser.parse_args()
    if args.command == "prepare":
        prepare(resolve(args.input), args.isolate, args.language)
    elif args.command == "assets":
        assets(resolve(args.plan))
    else:
        render(resolve(args.plan))


if __name__ == "__main__":
    main()
