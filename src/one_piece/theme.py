"""One Piece artwork catalog and SVG-to-cursor build pipeline."""

import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from theme import Cursor, Theme, linux, windows

from .art import (ARROW_OUT, PLUS, POINT_TIP, QMARK, aura_ring, badge, bone, brush, closed_hand, compass, crossed,
                 folded_ribbon, forbidden, hat, log_pose, luffy_pointing, meat, menu_card, open_hand, orbit, porthole, reach, scope,
                 yoru, yoru_working)
from .formats import windows as encode_windows, xcursor
from .preview import preview
from .svg import pulse, rot

FOLDER, TITLE = "OnePiece", "One Piece"  # theme folder / name shown in settings
X_SIZES, WIN_SIZES = (24, 32, 48, 64, 96), (32, 48, 64, 96)
HOLD = 3_600_000  # ms; cursors always loop, so a 1h last frame makes an animation play once


@dataclass(frozen=True)
class Drawing:
    cursor: Cursor
    frames: list[tuple[str, int]]
    hot: tuple[int, int]  # hotspot in `grid` units
    grid: int = 64
    zoom: float = 1  # Linux only; Windows cursors are a fixed size


def drawing(name, frames, hot, aliases="", win=None, grid=64, zoom=1):
    role, stem = win if win else (None, None)
    file = f"{stem}.{'ani' if len(frames) > 1 else 'cur'}" if stem else None
    cursor = Cursor(name, tuple((aliases or "").split()), role, file, aliases is not None)
    return Drawing(cursor, frames, hot, grid, zoom)


def still(body):
    return [(body, 0)]


# frames ---------------------------------------------------------------------------------------------------------------

ZOOM = 1.5  # Linux: pointer family, text, resize and grab drawn bigger than the rest; the link hand is 2x
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


def resize(deg):
    return still(rot(folded_ribbon(), deg))


# cursors --------------------------------------------------------------------------------------------------------------

DRAWINGS = [
    drawing("left_ptr", POINTER, PTR_HOT, "default arrow top_left_arrow wayland-cursor pointer-move", ("Arrow", "pointer"), zoom=ZOOM),
    drawing("right_ptr", still(f'<g transform="matrix(-1 0 0 1 64 0)">{PTR}</g>'), (64 - PTR_HOT[0], PTR_HOT[1]),
           "draft_large draft_small", zoom=ZOOM),
    drawing("question_arrow", still(badge(PTR, QMARK, (19, 44), 1.45)), PTR_HOT,
           "help left_ptr_help whats_this dnd-ask 5c6cd98b3f3ebcb1f9c7f1c204630408 d9ce0ab605698f320427677b458ad60b",
           ("Help", "help"), zoom=ZOOM),
    drawing("left_ptr_watch", WORKING, PTR_HOT,
           "progress 00000000000000020006000e7e9ffc3f 08e8e1c95fe2fc01f976f1e063a24ccd 3ecb610c1bf2410f44200f48c40d3599",
           ("AppStarting", "working"), zoom=ZOOM),
    drawing("wait", BUSY, (48, 48), "watch", ("Wait", "busy"), grid=96),
    drawing("crosshair", still(scope()), (32, 32),
           "cross cross_reverse diamond_cross tcross color-picker dotbox dot_box_mask draped_box icon target", ("Crosshair", "precision")),
    drawing("xterm", TEXT, (32, 32), "ibeam text", ("IBeam", "text"), zoom=ZOOM),
    drawing("vertical-text", [(rot(b, 90), ms) for b, ms in TEXT], (32, 32), zoom=ZOOM),
    drawing("pencil", still(brush()), (6, 58), "draft", ("NWPen", "handwriting")),
    drawing("crossed_circle", SHAKE, (32, 32),
           "not-allowed forbidden circle no-drop dnd_no_drop 03b6e0fcb3499374a867c041f52298f0", ("No", "unavailable")),
    drawing("sb_v_double_arrow", resize(90), (32, 32),
           "ns-resize row-resize double_arrow v_double_arrow size-ver size_ver split_v n-resize s-resize top_side "
           "bottom_side top_tee bottom_tee 00008160000006810000408080010102 2870a09082c103050810ffdffffe0204", ("SizeNS", "vert"), zoom=ZOOM),
    drawing("sb_h_double_arrow", resize(0), (32, 32),
           "ew-resize col-resize h_double_arrow size-hor size_hor split_h e-resize w-resize left_side right_side "
           "left_tee right_tee 028006030e0e7ebffc7f7070c0600140 14fef782d02440884392942c1120523", ("SizeWE", "horz"), zoom=ZOOM),
    drawing("bd_double_arrow", resize(45), (32, 32),
           "nwse-resize size_fdiag nw-resize se-resize top_left_corner bottom_right_corner ul_angle lr_angle "
           "c7088f0f3e6c8088236ef8e1e3e70000", ("SizeNWSE", "dgn1"), zoom=ZOOM),
    drawing("fd_double_arrow", resize(-45), (32, 32),
           "nesw-resize size_bdiag ne-resize sw-resize top_right_corner bottom_left_corner ur_angle ll_angle "
           "fcf1c3c7cd4491d801f1e1c78f100000", ("SizeNESW", "dgn2"), zoom=ZOOM),
    drawing("fleur", still(compass()), (32, 32),
           "move all-scroll size_all 4498f0e0c1937ffe01fd06f973665830 9081237383d90e509aa00f00170e968f", ("SizeAll", "move")),
    drawing("sb_up_arrow", still(reach(0)), (32, 5), "up-arrow center_ptr", ("UpArrow", "alternate")),
    drawing("sb_right_arrow", still(reach(90)), (59, 32), "right-arrow"),
    drawing("sb_down_arrow", still(reach(180)), (32, 59), "down-arrow"),
    drawing("sb_left_arrow", still(reach(-90)), (5, 32), "left-arrow"),
    drawing("hand2", still(luffy_pointing()), POINT_TIP,
           "pointer pointing_hand hand 9d800788f1b08800ae810202380a0822 e29285e634086352946a0e7090d73106", ("Hand", "link"), zoom=2),
    drawing("hand1", GRAB, (32, 32), "grab openhand", zoom=ZOOM),
    drawing("grabbing", GRABBING, (32, 32), "closedhand dnd-move dnd-none fcf21c00b30f7e3f83fe0dfd12e71cff", zoom=ZOOM),
    drawing("copy", still(badge(PTR, PLUS, BADGE_AT)), PTR_HOT,
           "dnd-copy 1081e37283d90000800003c07f3ef6bf 6407b0e94181790501fd1e167b474872 b66166c04f8c3109214a4fbd64a50fc8",
           zoom=ZOOM),
    drawing("link", still(badge(PTR, ARROW_OUT, BADGE_AT)), PTR_HOT,
           "alias dnd-link 3085a0e285430894940527032f8b26df 640fb0e74195791501fd1ed57b41487f a2a266d0498c3104214a47bd64ab0fc8",
           zoom=ZOOM),
    drawing("context-menu", still(menu_card(PTR, BADGE_AT)), PTR_HOT, zoom=ZOOM),
    drawing("X_cursor", still(crossed()), (32, 32), "pirate x-cursor"),
    drawing("zoom-in", still(porthole("+")), (26, 26)),
    drawing("zoom-out", still(porthole("-")), (26, 26)),
    drawing("plus", still(bone(10, 32, 54, 32) + bone(32, 10, 32, 54)), (32, 32), "cell"),
    drawing("pin", SWING, (32, 30), None, ("Pin", "pin")),
    drawing("person", still(hat(32, 40, 1.2)), (32, 32), None, ("Person", "person")),
]

CURSORS = tuple(d.cursor for d in DRAWINGS)
THEME = Theme(FOLDER, TITLE, CURSORS, f"{TITLE} cursors", linux_name=FOLDER, activate=True)


def build(output):
    """Export both platforms and their preview into one theme folder."""
    directory = output / "cursors"
    directory.mkdir(parents=True, exist_ok=True)
    scratch = Path("/tmp/ai")
    scratch.mkdir(parents=True, exist_ok=True)

    def encode(d, tmp):
        if d.cursor.linux:
            xcursor(d, X_SIZES, tmp, directory)
        if d.cursor.file:
            return d.cursor.file, encode_windows(d, WIN_SIZES)
        return None

    with tempfile.TemporaryDirectory(dir=scratch) as tmp, ThreadPoolExecutor() as pool:
        files = dict(filter(None, pool.map(lambda d: encode(d, Path(tmp)), DRAWINGS)))
    windows(THEME, files, output)
    linux(THEME, output)
    preview(DRAWINGS, output / "preview.png")
