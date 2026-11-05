"""JARVIS palette, artwork catalog, and ANI recoloring build pipeline."""

import struct
from functools import cache
from itertools import pairwise

from theme import Cursor, Theme, linux as package_linux, windows

from .ani import frames, verify
from .preview import preview
from .xcursor import SIZES, xcursor

TITLE = "Kinetik JARVIS"
FOLDER = "Kinetik-JARVIS"
# Graphite-blue housing, champagne-metal highlights, arc-reactor cyan LEDs.
METAL = (
    (0, (4, 7, 12)), (24, (17, 25, 35)), (55, (47, 57, 70)),
    (100, (118, 117, 106)), (160, (219, 192, 135)), (255, (255, 244, 218)),
)
CYAN = (120, 235, 255)


def cursor(role, file, names):
    name, *aliases = names.split()
    return Cursor(name, tuple(aliases), role, file)


# Windows scheme order also defines preview order; Linux names live alongside each role.
CURSORS = (
    cursor("Arrow", "Normal.ani", "left_ptr default arrow top_left_arrow context-menu copy dnd-copy alias dnd-link"),
    cursor("Help", "Help.ani", "question_arrow help left_ptr_help whats_this 5c6cd98b3f3ebcb1f9c7f1c204630408"),
    cursor("AppStarting", "WIB.ani",
           "left_ptr_watch progress 00000000000000020006000e7e9ffc3f 08e8e1c95fe2fc01f976f1e063a24ccd"),
    cursor("Wait", "Busy.ani", "watch wait busy"),
    cursor("Crosshair", "Acc.ani",
           "crosshair cross cross_reverse tcross diamond_cross cell plus color-picker zoom-in zoom-out X_cursor"),
    cursor("IBeam", "Text.ani", "xterm text ibeam vertical-text"),
    cursor("NWPen", "Lapiz.ani", "pencil draft"),
    cursor("No", "Una.ani",
           "crossed_circle not-allowed forbidden circle no-drop dnd_no_drop dnd-no-drop 03b6e0fcb3499374a867c041f52298f0"),
    cursor("SizeNS", "VR.ani",
           "sb_v_double_arrow ns-resize row-resize double_arrow v_double_arrow size-ver size_ver split_v "
           "n-resize s-resize top_side bottom_side top_tee bottom_tee 00008160000006810000408080010102 "
           "2870a09082c103050810ffdffffe0204"),
    cursor("SizeWE", "HR.ani",
           "sb_h_double_arrow ew-resize col-resize h_double_arrow size-hor size_hor split_h e-resize w-resize "
           "left_side right_side left_tee right_tee 028006030e0e7ebffc7f7070c0600140 14fef782d02440884392942c1120523"),
    cursor("SizeNWSE", "DR 1.ani",
           "bd_double_arrow nwse-resize size_fdiag nw-resize se-resize top_left_corner bottom_right_corner "
           "ul_angle lr_angle c7088f0f3e6c8088236ef8e1e3e70000"),
    cursor("SizeNESW", "DR 2.ani",
           "fd_double_arrow nesw-resize size_bdiag ne-resize sw-resize top_right_corner bottom_left_corner "
           "ur_angle ll_angle fcf1c3c7cd4491d801f1e1c78f100000"),
    cursor("SizeAll", "Move.ani",
           "fleur move all-scroll size_all grabbing closedhand dnd-move dnd-none "
           "4498f0e0c1937ffe01fd06f973665830 9081237383d90e509aa00f00170e968f"),
    cursor("UpArrow", "Alt.ani", "sb_up_arrow up-arrow center_ptr"),
    cursor("Hand", "Boton.ani", "hand2 pointer pointing_hand hand hand1 grab openhand "
           "9d800788f1b08800ae810202380a0822 e29285e634086352946a0e7090d73106"),
)
THEME = Theme(FOLDER, TITLE, CURSORS, "JARVIS-inspired Kinetik animated cursors")


@cache
def metal(value):
    for (low, a), (high, b) in pairwise(METAL):
        if value <= high:
            weight = (value - low) / (high - low)
            return tuple(round(x + (y - x) * weight) for x, y in zip(a, b))
    return METAL[-1][1]


def recolor(data):
    source_frames = frames(data, allow_legacy=True)
    output = bytearray(data)
    struct.pack_into("<I", output, 4, len(output) - 8)
    for frame in source_frames:
        for pos in range(frame.offset, frame.end, 4):
            _, green, red, alpha = data[pos:pos + 4]
            if not alpha:
                continue
            # Source LEDs mix turquoise (0, 255, 217) with neutral metal.
            glow = max(0, green - red) / max(1, 255 - red)
            rgb = tuple(round(a + (b - a) * glow) for a, b in zip(metal(red), CYAN))
            output[pos:pos + 3] = bytes(reversed(rgb))
    verify(data, output)
    return bytes(output)


def linux(cursors, output):
    directory = output / "cursors"
    directory.mkdir(parents=True, exist_ok=True)
    for cursor in CURSORS:
        (directory / cursor.name).write_bytes(xcursor(cursors[cursor.file]))
    package_linux(THEME, output)


def build(source, output):
    cursors = {cursor.file: recolor((source / cursor.file).read_bytes()) for cursor in CURSORS}
    output.mkdir(parents=True, exist_ok=True)
    windows(THEME, cursors, output)
    linux(cursors, output)
    preview(cursors, output / "preview.png")
    total = sum(len(frames(data)) for data in cursors.values())
    print(f"Built Windows and Linux themes: {len(cursors)} animated cursors, {total} source frames: {output}")
    print(f"Linux sizes: {', '.join(map(str, SIZES))} px")
    print("Verified identical geometry, alpha, AND masks, hotspots, timing and animation sequences.")
