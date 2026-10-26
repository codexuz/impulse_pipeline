"""
Python <-> Remotion ko'prigi (faqat video): fayllarni remotion/public/runs/<run_id>/ ga joylash, props yozish va render chaqirish.

Remotion faqat o'z public/ papkasidagi fayllarni ko'radi, shuning uchun har bir render uchun kerakli
media shu yerga hardlink (bo'lmasa nusxa) qilinadi va props ichida "runs/<run_id>/..." yo'li beriladi.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTION_DIR = ROOT / "remotion"
PUBLIC_DIR = REMOTION_DIR / "public"
RUNS_DIR = PUBLIC_DIR / "runs"
BRAND = json.loads((ROOT / "config/brand_preset.json").read_text(encoding="utf-8"))


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rel(path: str | Path) -> str:
    p = resolve(path).resolve()
    return p.relative_to(ROOT.resolve()).as_posix() if p.is_relative_to(ROOT.resolve()) else p.as_posix()


class Stage:
    """Bitta render uchun public/runs/<run_id>/ papkasi."""

    def __init__(self, run_id: str, clean: bool = True):
        self.run_id = run_id
        self.dir = RUNS_DIR / run_id
        if clean and self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._seen: dict[Path, str] = {}

    def add(self, path: str | Path | None, name: str | None = None) -> str:
        """Faylni joylaydi va Remotion staticFile() uchun yo'lni qaytaradi. Bo'sh/yo'q fayl -> ""."""
        if not path:
            return ""
        src = resolve(path).resolve()
        if not src.exists():
            print(f"[ogohlantirish] fayl topilmadi: {path}")
            return ""
        if src in self._seen:
            return self._seen[src]
        dest = self.dir / (name or src.name)
        if dest.exists():
            dest = dest.with_name(f"{dest.stem}_{len(self._seen)}{dest.suffix}")
        try:
            os.link(src, dest)  # bir xil diskda bir zumda, joy egallamaydi
        except OSError:
            shutil.copy2(src, dest)
        staged = f"runs/{self.run_id}/{dest.name}"
        self._seen[src] = staged
        return staged

    def write_props(self, props: dict, name: str = "props.json") -> Path:
        path = self.dir / name
        path.write_text(json.dumps(props, indent=1, ensure_ascii=False), encoding="utf-8")
        return path

    def cleanup(self) -> None:
        # Render tugagach vaqtinchalik fayllar o'chiriladi (asl fayllar assets/ va workspace/ da qoladi)
        shutil.rmtree(self.dir, ignore_errors=True)


def _npx() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def ensure_node_modules() -> None:
    if not (REMOTION_DIR / "node_modules").exists():
        subprocess.run([_npx(), "--yes", "npm", "install"], cwd=REMOTION_DIR, check=True)


def render_video(composition: str, props_path: Path, out_path: Path, extra: list[str] | None = None) -> Path:
    ensure_node_modules()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_npx(), "remotion", "render", composition, str(out_path), f"--props={props_path}",
           "--codec=h264", f"--crf={BRAND['video_settings']['crf']}", *(extra or [])]
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True)
    return out_path
