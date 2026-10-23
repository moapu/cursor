"""Cursor themes: XCursor for Linux, .cur/.ani + install.inf for Windows. Builds the themes named, or all of them.

nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py [onepiece] [aot]
"""

import importlib
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from cursor import ROLES
from formats import inf, render, windows, xcursor

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
THEMES = ("onepiece", "aot")  # packages under src/
X_SIZES, WIN_SIZES = (24, 32, 48, 64, 96), (32, 48, 64, 96)


def build(c, tmp, x_dir, win_dir):
    """Write one cursor in every format it has; returns (Windows stem, file name) or None."""
    if c.aliases is not None:
        xcursor(c, X_SIZES, tmp, x_dir / "cursors")
    if not c.win:
        return None
    return c.win, windows(c, WIN_SIZES, win_dir)


def preview(cursors, out):
    """Contact sheet of every cursor's longest (rest) frame."""
    cell = 72
    sheet = Image.new("RGBA", (cell * 8, cell * ((len(cursors) + 7) // 8)), "#9aa0ac")
    for i, c in enumerate(cursors):
        rest = max(c.frames, key=lambda f: f[1])[0]
        sheet.alpha_composite(render(rest, 64, c.grid), (i % 8 * cell + 4, i // 8 * cell + 4))
    sheet.save(out)


def theme(pkg):
    t = importlib.import_module(pkg)
    x_dir, win_dir = ROOT / t.NAME, ROOT / f"{t.NAME}-Windows"
    for d in (x_dir, win_dir):
        shutil.rmtree(d, ignore_errors=True)
    (x_dir / "cursors").mkdir(parents=True)
    win_dir.mkdir()
    for f in ("index.theme", "cursor.theme"):
        (x_dir / f).write_text(f"[Icon Theme]\nName={t.NAME}\nComment={t.TITLE} cursors\n")
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor() as pool:
        files = dict(filter(None, pool.map(lambda c: build(c, Path(tmp), x_dir, win_dir), t.CURSORS)))
    inf(ROLES, {role: files[stem] for role, stem in ROLES.items()}, win_dir, t.NAME, t.TITLE)
    preview(t.CURSORS, SRC / pkg / "preview.png")


def main():
    for pkg in sys.argv[1:] or THEMES:
        theme(pkg)


if __name__ == "__main__":
    main()
