"""
Studio edit: the speaker without their background (scripts/matte_video.py) in an animated Impulse studio (Remotion `Studio`).

Plan: workspace/03_edit_plans/<id>.studio.json — matte, captions (word timings from the Scribe transcript, text checked
against what was really said), zooms, emojis, badges, callouts, headlines, end card, SFX and music.

  python scripts/matte_video.py workspace/01_raw/<id>.mp4 --grade          # cut-out + shadows lifted, colour cast removed
  python scripts/studio_render.py workspace/03_edit_plans/<id>.studio.json            # -> workspace/04_exports/<id>.mp4
  python scripts/studio_render.py workspace/03_edit_plans/<id>.studio.json --stills 1.0,5.0,8.0   # quick frame check
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_emoji import fetch as fetch_emoji  # noqa: E402
from remotion_utils import BRAND, REMOTION_DIR, Stage, _npx, ensure_node_modules, rel, render_video, resolve  # noqa: E402

VIDEO = BRAND["video_settings"]


def gain(db: float) -> float:
    return round(10 ** (db / 20), 4)


def probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def build_props(plan: dict, stage: Stage) -> dict:
    matte = resolve(plan["matte"])
    if not matte.exists():
        raise SystemExit(f"Matte yo'q: {plan['matte']} — avval python scripts/matte_video.py {plan.get('source', '<video>')} --grade")
    matte_duration = probe_duration(matte)

    def emoji(name: str | None, skin: str | None = None) -> str:
        return stage.add(fetch_emoji(name, skin=skin or "Default")) if name else ""

    pages = []
    for page in plan.get("captions", []):
        words = [{"text": w[0], "start": w[1], "end": w[2], "highlight": bool(w[3]) if len(w) > 3 else False} for w in page]
        pages.append({"start": words[0]["start"] - 0.08, "end": words[-1]["end"] + 0.35, "words": words})
    for a, b in zip(pages, pages[1:]):  # pages never overlap
        a["end"] = min(a["end"], b["start"])

    audio = plan.get("audio", {})
    bgm = audio.get("bgm")
    end = plan.get("end_card")
    return {
        "fps": VIDEO["fps"],
        "durationInSeconds": plan.get("duration") or round(matte_duration, 3),
        "matte": stage.add(matte, "matte.webm"),
        "matteDuration": round(matte_duration, 3),
        "logo": stage.add(plan.get("logo", BRAND["brand"]["logo_full"])),
        "voiceVolume": audio.get("voice_volume", 1.0),
        "subject": {"scale": plan.get("subject", {}).get("scale", 1.0), "offsetY": plan.get("subject", {}).get("offsetY", 0)},
        "captionPages": pages,
        "zooms": plan.get("zooms", []),
        "emojis": [{"src": emoji(e["name"], e.get("skin")), "x": e["x"], "y": e["y"], "size": e.get("size", 200),
                    "rotate": e.get("rotate", 0), "start": e["start"], "end": e["end"]} for e in plan.get("emojis", [])],
        "badges": plan.get("badges", []),
        "callouts": [{**{k: c[k] for k in ("title", "subtitle", "side", "y", "start", "end")}, "emoji": emoji(c.get("emoji"), c.get("skin"))}
                     for c in plan.get("callouts", [])],
        "headlines": [{**{k: h[k] for k in ("text", "accent", "start", "end")}, "backdrop": h.get("backdrop", ""),
                       "emoji": emoji(h.get("emoji"), h.get("skin"))} for h in plan.get("headlines", [])],
        "endCard": {"start": end["start"], "title": end.get("title", ""), "contacts": end.get("contacts", [])} if end else None,
        "bgm": {"src": stage.add(bgm["file"]), "volume": gain(bgm.get("volume_db", -15)), "duckVolume": gain(bgm.get("duck_db", -24))}
        if bgm and resolve(bgm["file"]).exists() else None,
        "sfx": [{"src": stage.add(s["file"]), "at": s["at"], "volume": gain(s.get("volume_db", -8))}
                for s in audio.get("sfx", []) if resolve(s["file"]).exists()],
    }


def render(plan_path: Path, stills: list[float] | None) -> None:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    stage = Stage(f"studio_{plan['id']}")
    out = resolve(plan.get("output") or f"workspace/04_exports/{plan['id']}.mp4")
    try:
        props_path = stage.write_props(build_props(plan, stage))
        if stills:
            ensure_node_modules()
            for t in stills:
                still = out.with_name(f"{out.stem}_still_{t:.1f}s.png")
                subprocess.run([_npx(), "remotion", "still", "Studio", str(still), f"--props={props_path}",
                                f"--frame={round(t * VIDEO['fps'])}"], cwd=REMOTION_DIR, check=True)
                print(f"[still] {rel(still)}")
        else:
            render_video("Studio", props_path, out)
            print(f"[render] {rel(out)}")
    finally:
        stage.cleanup()


def main() -> None:
    p = argparse.ArgumentParser(description="Studio edit (Remotion `Studio`)")
    p.add_argument("plan")
    p.add_argument("--stills", help="Faqat kadrlar: 1.0,5.0,8.0 (soniya)")
    a = p.parse_args()
    render(resolve(a.plan), [float(x) for x in a.stills.split(",")] if a.stills else None)


if __name__ == "__main__":
    main()
