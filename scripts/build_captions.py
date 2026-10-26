"""
Scribe transkripsiyasidan Remotion uchun subtitr sahifalari (1–3 so'z) yasaydi va kalit so'zlarni belgilaydi.

Kalit so'zlar edit_plan.json -> "keywords":
  {"english": ["over the moon"], "correct": ["I was thrilled"], "mistake": ["very happy"]}
Ranglar Remotion'da brand_preset.json dan olinadi: english sariq, correct yashil, mistake qizil.

Natija: workspace/02_transcripts/<nom>.captions.json
  [{"startMs", "endMs", "words": [{"text", "startMs", "endMs", "style": null|"english"|"correct"|"mistake"}]}]

Ishlatish:
  python scripts/build_captions.py workspace/02_transcripts/speaking_part2_cut.json --plan workspace/03_edit_plans/speaking_part2.json
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES = ("english", "correct", "mistake")

MAX_WORDS = 3
MAX_CHARS = 22
MAX_GAP = 0.45
MAX_HOLD = 0.6


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    return p.relative_to(ROOT.resolve()).as_posix() if p.is_relative_to(ROOT.resolve()) else p.as_posix()


def _norm(token: str) -> str:
    return re.sub(r"[^\w'.]", "", token.lower()).strip(".")


def mark_keywords(words: list[dict], keywords: dict[str, list[str]]) -> list[str | None]:
    """Har bir so'z uchun stil nomi yoki None. Ko'p so'zli iboralar ham topiladi."""
    marks: list[str | None] = [None] * len(words)
    normed = [_norm(w["word"]) for w in words]
    # Uzunroq iboralar birinchi — "over the moon" "moon" dan ustun
    phrases = sorted(
        ((style, [_norm(t) for t in phrase.split()]) for style, items in keywords.items() for phrase in items),
        key=lambda x: -len(x[1]),
    )
    for style, tokens in phrases:
        if style not in STYLES or not tokens:
            continue
        n = len(tokens)
        for i in range(len(normed) - n + 1):
            if normed[i:i + n] == tokens and all(m is None for m in marks[i:i + n]):
                marks[i:i + n] = [style] * n
    return marks


def chunk_words(words: list[dict], marks: list[str | None]) -> list[list[int]]:
    chunks, current = [], []
    for i, w in enumerate(words):
        if current:
            prev = words[current[-1]]
            text_len = sum(len(words[j]["word"]) + 1 for j in current) + len(w["word"])
            same_phrase = marks[i] is not None and marks[i] == marks[current[-1]]
            too_long = len(current) >= MAX_WORDS or text_len > MAX_CHARS
            if (w["start"] - prev["end"] > MAX_GAP) or (too_long and not same_phrase) or re.search(r"[.?!]$", prev["word"]):
                chunks.append(current)
                current = []
        current.append(i)
    if current:
        chunks.append(current)
    return chunks


def build_pages(words: list[dict], keywords: dict[str, list[str]]) -> list[dict]:
    words = [w for w in words if w["word"]]
    marks = mark_keywords(words, keywords)
    pages = []
    for chunk in chunk_words(words, marks):
        last = words[chunk[-1]]
        end = last["end"]
        nxt = chunk[-1] + 1
        if nxt < len(words):
            # Keyingi sahifa boshlanguncha ekranda qoladi (miltillamaslik uchun), lekin MAX_HOLD dan ko'p emas
            end = min(max(end, words[nxt]["start"]), last["end"] + MAX_HOLD)
        pages.append({
            "startMs": round(words[chunk[0]]["start"] * 1000),
            "endMs": round(end * 1000),
            "words": [
                {"text": words[j]["word"], "startMs": round(words[j]["start"] * 1000),
                 "endMs": round(words[j]["end"] * 1000), "style": marks[j]}
                for j in chunk
            ],
        })
    return pages


def build_captions(transcript_path: Path, plan_path: Path | None = None) -> Path:
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path else {}
    pages = build_pages(transcript["words"], plan.get("keywords", {}))
    out = transcript_path.with_name(f"{transcript_path.stem}.captions.json")
    out.write_text(json.dumps(pages, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[captions] {_rel(out)} — {len(pages)} ta sahifa")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Remotion subtitr sahifalari")
    parser.add_argument("transcript", help="transcribe_elevenlabs.py yaratgan .json")
    parser.add_argument("--plan", help="edit_plan.json (keywords uchun)")
    args = parser.parse_args()

    resolve = lambda p: Path(p) if Path(p).is_absolute() else ROOT / p
    build_captions(resolve(args.transcript), resolve(args.plan) if args.plan else None)


if __name__ == "__main__":
    main()
