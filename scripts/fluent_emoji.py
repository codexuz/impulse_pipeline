"""
Microsoft Fluent Emoji 3D (MIT litsenziya) — nomi yoki emoji belgisi bo'yicha PNG yuklab, keshlaydi.

Kesh: assets/emoji/fluent3d/<slug>.png  (indeks: assets/emoji/fluent3d/_index.json)

Ishlatish:
  python scripts/fluent_emoji.py "party popper" trophy 🎯
  python scripts/fluent_emoji.py --search moon
  python scripts/fluent_emoji.py "thumbs up" --skin Medium
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMOJI_DIR = ROOT / "assets/emoji/fluent3d"
INDEX_FILE = EMOJI_DIR / "_index.json"
TREE_URL = "https://api.github.com/repos/microsoft/fluentui-emoji/git/trees/main?recursive=1"
CDN_BASE = "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/"

# Unicode nomi Fluent papka nomidan farq qiladigan holatlar
ALIASES = {
    "direct hit": "Bullseye",
    "target": "Bullseye",
    "calendar": "Spiral calendar",
    "check": "Check mark button",
    "cross": "Cross mark",
    "100": "Hundred points",
    "headphones": "Headphone",
    "mic": "Studio microphone",
    "book": "Open book",
    "idea": "Light bulb",
    "medal": "Sports medal",
}
SKIN_TONES = ("Default", "Light", "Medium-Light", "Medium", "Medium-Dark", "Dark")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "impulse-pipeline"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def load_index(refresh: bool = False) -> dict[str, list[str]]:
    """{papka_nomi: [3D png yo'llari]} — GitHub daraxtidan bir marta olinadi."""
    if INDEX_FILE.exists() and not refresh:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    tree = json.loads(_get(TREE_URL))["tree"]
    index: dict[str, list[str]] = {}
    for item in tree:
        path = item["path"]
        if "/3D/" in path and path.endswith(".png"):
            index.setdefault(path.split("/")[1], []).append(path)
    EMOJI_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
    return index


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _glyph_name(text: str) -> str | None:
    chars = [c for c in text if c not in "️‍"]
    if len(chars) == 1 and ord(chars[0]) > 0x2000:
        try:
            return unicodedata.name(chars[0]).lower()
        except ValueError:
            return None
    return None


def resolve(query: str, index: dict[str, list[str]]) -> str:
    """Emoji belgisi, inglizcha nom yoki alias -> Fluent papka nomi."""
    name = (_glyph_name(query) or query).strip().lower()
    if name in ALIASES:
        return ALIASES[name]
    by_lower = {folder.lower(): folder for folder in index}
    if name in by_lower:
        return by_lower[name]
    close = difflib.get_close_matches(name, list(by_lower), n=1, cutoff=0.75)
    if close:
        return by_lower[close[0]]
    hints = [f for f in index if name.split()[0] in f.lower()][:8]
    raise KeyError(f"Fluent emoji topilmadi: '{query}'. O'xshashlari: {hints}")


def fetch(query: str, skin: str = "Default", refresh_index: bool = False) -> Path:
    index = load_index(refresh_index)
    folder = resolve(query, index)
    paths = index[folder]
    # Teri rangi variantlari bo'lsa — tanlangani, aks holda yagona 3D fayl
    chosen = next((p for p in paths if f"/{skin}/3D/" in p), None) or next(
        (p for p in paths if "/Default/3D/" in p), None) or paths[0]
    out = EMOJI_DIR / f"{slugify(folder)}{'' if skin == 'Default' else '_' + slugify(skin)}.png"
    if not out.exists():
        out.write_bytes(_get(CDN_BASE + urllib.parse.quote(chosen)))
        print(f"[emoji] {folder} -> {out.relative_to(ROOT).as_posix()}")
    return out


def search(term: str) -> list[str]:
    term = term.lower()
    return [f for f in load_index() if term in f.lower()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fluent Emoji 3D yuklovchi")
    parser.add_argument("names", nargs="*", help="Nomlar yoki emoji belgilari")
    parser.add_argument("--skin", default="Default", choices=SKIN_TONES)
    parser.add_argument("--search", help="Papka nomlari ichidan qidirish")
    parser.add_argument("--refresh-index", action="store_true")
    args = parser.parse_args()

    if args.search:
        print("\n".join(search(args.search)) or "topilmadi")
        return
    if not args.names:
        parser.error("kamida bitta emoji nomi kerak")
    failed = False
    for name in args.names:
        try:
            print(fetch(name, args.skin, args.refresh_index).relative_to(ROOT).as_posix())
        except KeyError as e:
            print(e, file=sys.stderr)
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
