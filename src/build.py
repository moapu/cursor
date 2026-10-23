"""One Piece cursor theme: XCursor for Linux, .cur/.ani + install.inf for Windows.

nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
"""

import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from art import (ARROW_OUT, PLUS, POINT_TIP, QMARK, aura_ring, badge, bone, brush, closed_hand, compass, crocodile_hook,
                 crossed, forbidden, hat, log_pose, luffy_pointing, meat, menu_card, open_hand, orbit, porthole, reach, scope,
                 yoru, yoru_working)
from formats import inf, render, windows, xcursor
from svg import pulse, rot

NAME, TITLE = "OnePiece", "One Piece"  # theme folder / name shown in settings
ROOT = Path(__file__).resolve().parent.parent
X_DIR, WIN_DIR = ROOT / NAME, ROOT / f"{NAME}-Windows"
X_SIZES, WIN_SIZES = (24, 32, 48, 64, 96), (32, 48, 64, 96)
HOLD = 3_600_000  # ms; cursors always loop, so a 1h last frame makes an animation play once


@dataclass
class Cursor:
    name: str
    frames: list  # [(svg body, delay ms)]
    hot: tuple  # hotspot in `grid` units
    aliases: str | None = ""  # None: Windows only
    win: str | None = None  # Windows file stem
    grid: int = 64  # canvas size the body is drawn on
    win_view: int = 64  # Windows viewBox
    zoom: float = 1  # Linux only: drawn this much bigger (Windows cursors are a fixed size)


def still(body):
    return [(body, 0)]


# frames ---------------------------------------------------------------------------------------------------------------

ZOOM = 1.5  # Linux: pointer family, text and grab drawn bigger than the rest; the link hand is 2x
PTR_HOT, BADGE_AT = (5, 4), (16, 47)
POINTER = [(yoru(), 2400)] + [(yoru(glint=g), 35) for g in range(36, -6, -6)]  # a shine runs down the blade
PTR = POINTER[0][0]
WORKING = [(yoru_working(i), 90) for i in range(12)]
BUSY = [(aura_ring(48, 50, 30, i % 12) + orbit(a, 48, 50, 17, 0.8), 45) for i, a in enumerate(range(0, 360, 15))]
TEXT = still(meat())
SHAKE = [(forbidden(0), 1500)] + [(forbidden(d, f), 45) for d, f in ((-12, .5), (12, .8), (-10, .9), (10, .8), (-6, .6), (6, .4), (0, .2))]
SWING = [(log_pose(n), 70) for n in (-35, 20, -14, 8, -4, 0)] + [(log_pose(0), HOLD)]
GRAB = [(open_hand(1 + .03 * pulse(i)), 120) for i in range(12)]
GRABBING = [(closed_hand(1 - .04 * pulse(i)), 120) for i in range(12)]


def resize(deg, flip_y=False):
    body = rot(crocodile_hook(), deg)
    if flip_y:
        body = f'<g transform="translate(0 64) scale(1 -1)">{body}</g>'
    return still(body)


# cursors --------------------------------------------------------------------------------------------------------------

CURSORS = [
    Cursor("left_ptr", POINTER, PTR_HOT, "default arrow top_left_arrow wayland-cursor pointer-move", "pointer", zoom=ZOOM),
    Cursor("right_ptr", still(f'<g transform="matrix(-1 0 0 1 64 0)">{PTR}</g>'), (64 - PTR_HOT[0], PTR_HOT[1]),
           "draft_large draft_small", zoom=ZOOM),
    Cursor("question_arrow", still(badge(PTR, QMARK, (19, 44), 1.45)), PTR_HOT,
           "help left_ptr_help whats_this dnd-ask 5c6cd98b3f3ebcb1f9c7f1c204630408 d9ce0ab605698f320427677b458ad60b",
           "help", zoom=ZOOM),
    Cursor("left_ptr_watch", WORKING, PTR_HOT,
           "progress 00000000000000020006000e7e9ffc3f 08e8e1c95fe2fc01f976f1e063a24ccd 3ecb610c1bf2410f44200f48c40d3599",
           "working", zoom=ZOOM),
    Cursor("wait", BUSY, (48, 48), "watch", "busy", grid=96, win_view=96),
    Cursor("crosshair", still(scope()), (32, 32),
           "cross cross_reverse diamond_cross tcross color-picker dotbox dot_box_mask draped_box icon target", "precision"),
    Cursor("xterm", TEXT, (32, 32), "ibeam text", "text", zoom=ZOOM),
    Cursor("vertical-text", [(rot(b, 90), ms) for b, ms in TEXT], (32, 32), zoom=ZOOM),
    Cursor("pencil", still(brush()), (6, 58), "draft", "handwriting"),
    Cursor("crossed_circle", SHAKE, (32, 32),
           "not-allowed forbidden circle no-drop dnd_no_drop 03b6e0fcb3499374a867c041f52298f0", "unavailable"),
    Cursor("sb_v_double_arrow", resize(90), (32, 32),
           "ns-resize row-resize double_arrow v_double_arrow size-ver size_ver split_v n-resize s-resize top_side "
           "bottom_side top_tee bottom_tee 00008160000006810000408080010102 2870a09082c103050810ffdffffe0204", "vert"),
    Cursor("sb_h_double_arrow", resize(0), (32, 32),
           "ew-resize col-resize h_double_arrow size-hor size_hor split_h e-resize w-resize left_side right_side "
           "left_tee right_tee 028006030e0e7ebffc7f7070c0600140 14fef782d02440884392942c1120523", "horz"),
    Cursor("bd_double_arrow", resize(45), (32, 32),
           "nwse-resize size_fdiag nw-resize se-resize top_left_corner bottom_right_corner ul_angle lr_angle "
           "c7088f0f3e6c8088236ef8e1e3e70000", "dgn1"),
    Cursor("fd_double_arrow", resize(-45), (32, 32),
           "nesw-resize size_bdiag ne-resize sw-resize top_right_corner bottom_left_corner ur_angle ll_angle "
           "fcf1c3c7cd4491d801f1e1c78f100000", "dgn2"),
    Cursor("fleur", still(compass()), (32, 32),
           "move all-scroll size_all 4498f0e0c1937ffe01fd06f973665830 9081237383d90e509aa00f00170e968f", "move"),
    Cursor("sb_up_arrow", still(reach(0)), (32, 5), "up-arrow center_ptr", "alternate"),
    Cursor("sb_right_arrow", still(reach(90)), (59, 32), "right-arrow"),
    Cursor("sb_down_arrow", still(reach(180)), (32, 59), "down-arrow"),
    Cursor("sb_left_arrow", still(reach(-90)), (5, 32), "left-arrow"),
    Cursor("hand2", still(luffy_pointing()), POINT_TIP,
           "pointer pointing_hand hand 9d800788f1b08800ae810202380a0822 e29285e634086352946a0e7090d73106", "link", zoom=2),
    Cursor("hand1", GRAB, (32, 32), "grab openhand", zoom=ZOOM),
    Cursor("grabbing", GRABBING, (32, 32), "closedhand dnd-move dnd-none fcf21c00b30f7e3f83fe0dfd12e71cff", zoom=ZOOM),
    Cursor("copy", still(badge(PTR, PLUS, BADGE_AT)), PTR_HOT,
           "dnd-copy 1081e37283d90000800003c07f3ef6bf 6407b0e94181790501fd1e167b474872 b66166c04f8c3109214a4fbd64a50fc8",
           zoom=ZOOM),
    Cursor("link", still(badge(PTR, ARROW_OUT, BADGE_AT)), PTR_HOT,
           "alias dnd-link 3085a0e285430894940527032f8b26df 640fb0e74195791501fd1ed57b41487f a2a266d0498c3104214a47bd64ab0fc8",
           zoom=ZOOM),
    Cursor("context-menu", still(menu_card(PTR, BADGE_AT)), PTR_HOT, zoom=ZOOM),
    Cursor("X_cursor", still(crossed()), (32, 32), "pirate x-cursor"),
    Cursor("zoom-in", still(porthole("+")), (26, 26)),
    Cursor("zoom-out", still(porthole("-")), (26, 26)),
    Cursor("plus", still(bone(10, 32, 54, 32) + bone(32, 10, 32, 54)), (32, 32), "cell"),
    Cursor("pin", SWING, (32, 30), None, "pin"),
    Cursor("person", still(hat(32, 40, 1.2)), (32, 32), None, "person"),
]

# Extra Windows assets: wrist outside the dragged edge, hook facing into the window.
RESIZE_ANGLES = {"n": -90, "ne": -45, "e": 0, "se": 45, "s": 90, "sw": 135, "w": 180, "nw": -135}
DIRECTIONAL_RESIZE = [
    Cursor(f"resize-{direction}", resize(deg, flip_y=direction == "e"), (32, 32), None, f"resize-{direction}")
    for direction, deg in RESIZE_ANGLES.items()
]

# Windows registry role -> file stem, in Control Panel scheme order
ROLES = {
    "Arrow": "pointer", "Help": "help", "AppStarting": "working", "Wait": "busy", "Crosshair": "precision", "IBeam": "text",
    "NWPen": "handwriting", "No": "unavailable", "SizeNS": "vert", "SizeWE": "horz", "SizeNWSE": "dgn1", "SizeNESW": "dgn2",
    "SizeAll": "move", "UpArrow": "alternate", "Hand": "link", "Pin": "pin", "Person": "person",
}


# main -----------------------------------------------------------------------------------------------------------------


def build(c, tmp):
    """Write one cursor in every format it has; returns (Windows stem, file name) or None."""
    if c.aliases is not None:
        xcursor(c, X_SIZES, tmp, X_DIR / "cursors")
    if not c.win:
        return None
    return c.win, windows(c, WIN_SIZES, WIN_DIR)


def preview():
    """Contact sheet of every cursor's longest (rest) frame."""
    cell = 72
    sheet = Image.new("RGBA", (cell * 8, cell * ((len(CURSORS) + 7) // 8)), "#9aa0ac")
    for i, c in enumerate(CURSORS):
        rest = max(c.frames, key=lambda f: f[1])[0]
        sheet.alpha_composite(render(rest, 64, c.grid), (i % 8 * cell + 4, i // 8 * cell + 4))
    sheet.save(Path(__file__).with_name("preview.png"))


def main():
    for d in (X_DIR, WIN_DIR):
        shutil.rmtree(d, ignore_errors=True)
    (X_DIR / "cursors").mkdir(parents=True)
    WIN_DIR.mkdir()
    for f in ("index.theme", "cursor.theme"):
        (X_DIR / f).write_text(f"[Icon Theme]\nName={NAME}\nComment={TITLE} cursors\n")
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor() as pool:
        files = dict(filter(None, pool.map(lambda c: build(c, Path(tmp)), CURSORS + DIRECTIONAL_RESIZE)))
    inf(ROLES, {role: files[stem] for role, stem in ROLES.items()}, WIN_DIR, NAME, TITLE)
    preview()


if __name__ == "__main__":
    main()
