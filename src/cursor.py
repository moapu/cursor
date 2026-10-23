"""What a theme defines: Cursor slots, with the XCursor aliases and Windows roles every theme shares."""

from dataclasses import dataclass

HOLD = 3_600_000  # ms; cursors always loop, so a 1h last frame makes an animation play once
ZOOM = 1.5  # Linux: pointer family, text and grab drawn bigger than the rest

# cursor name -> (XCursor aliases or None for Windows only, Windows file stem or None)
SLOTS = {
    "left_ptr": ("default arrow top_left_arrow wayland-cursor pointer-move", "pointer"),
    "right_ptr": ("draft_large draft_small", None),
    "question_arrow": ("help left_ptr_help whats_this dnd-ask 5c6cd98b3f3ebcb1f9c7f1c204630408 d9ce0ab605698f320427677b458ad60b",
                       "help"),
    "left_ptr_watch": ("progress 00000000000000020006000e7e9ffc3f 08e8e1c95fe2fc01f976f1e063a24ccd 3ecb610c1bf2410f44200f48c40d3599",
                       "working"),
    "wait": ("watch", "busy"),
    "crosshair": ("cross cross_reverse diamond_cross tcross color-picker dotbox dot_box_mask draped_box icon target", "precision"),
    "xterm": ("ibeam text", "text"),
    "vertical-text": ("", None),
    "pencil": ("draft", "handwriting"),
    "crossed_circle": ("not-allowed forbidden circle no-drop dnd_no_drop 03b6e0fcb3499374a867c041f52298f0", "unavailable"),
    "sb_v_double_arrow": ("ns-resize row-resize double_arrow v_double_arrow size-ver size_ver split_v n-resize s-resize top_side "
                          "bottom_side top_tee bottom_tee 00008160000006810000408080010102 2870a09082c103050810ffdffffe0204", "vert"),
    "sb_h_double_arrow": ("ew-resize col-resize h_double_arrow size-hor size_hor split_h e-resize w-resize left_side right_side "
                          "left_tee right_tee 028006030e0e7ebffc7f7070c0600140 14fef782d02440884392942c1120523", "horz"),
    "bd_double_arrow": ("nwse-resize size_fdiag nw-resize se-resize top_left_corner bottom_right_corner ul_angle lr_angle "
                        "c7088f0f3e6c8088236ef8e1e3e70000", "dgn1"),
    "fd_double_arrow": ("nesw-resize size_bdiag ne-resize sw-resize top_right_corner bottom_left_corner ur_angle ll_angle "
                        "fcf1c3c7cd4491d801f1e1c78f100000", "dgn2"),
    "fleur": ("move all-scroll size_all 4498f0e0c1937ffe01fd06f973665830 9081237383d90e509aa00f00170e968f", "move"),
    "sb_up_arrow": ("up-arrow center_ptr", "alternate"),
    "sb_right_arrow": ("right-arrow", None),
    "sb_down_arrow": ("down-arrow", None),
    "sb_left_arrow": ("left-arrow", None),
    "hand2": ("pointer pointing_hand hand 9d800788f1b08800ae810202380a0822 e29285e634086352946a0e7090d73106", "link"),
    "hand1": ("grab openhand", None),
    "grabbing": ("closedhand dnd-move dnd-none fcf21c00b30f7e3f83fe0dfd12e71cff", None),
    "copy": ("dnd-copy 1081e37283d90000800003c07f3ef6bf 6407b0e94181790501fd1e167b474872 b66166c04f8c3109214a4fbd64a50fc8", None),
    "link": ("alias dnd-link 3085a0e285430894940527032f8b26df 640fb0e74195791501fd1ed57b41487f a2a266d0498c3104214a47bd64ab0fc8",
             None),
    "context-menu": ("", None),
    "X_cursor": ("pirate x-cursor", None),
    "zoom-in": ("", None),
    "zoom-out": ("", None),
    "plus": ("cell", None),
    "pin": (None, "pin"),
    "person": (None, "person"),
}

# Windows registry role -> file stem, in Control Panel scheme order
ROLES = {
    "Arrow": "pointer", "Help": "help", "AppStarting": "working", "Wait": "busy", "Crosshair": "precision", "IBeam": "text",
    "NWPen": "handwriting", "No": "unavailable", "SizeNS": "vert", "SizeWE": "horz", "SizeNWSE": "dgn1", "SizeNESW": "dgn2",
    "SizeAll": "move", "UpArrow": "alternate", "Hand": "link", "Pin": "pin", "Person": "person",
}


@dataclass
class Cursor:
    name: str  # a SLOTS key
    frames: list  # [(svg body, delay ms)]
    hot: tuple  # hotspot in `grid` units
    grid: int = 64  # canvas size the body is drawn on
    zoom: float = 1  # Linux only: drawn this much bigger (Windows cursors are a fixed size)

    @property
    def aliases(self):  # None: Windows only
        return SLOTS[self.name][0]

    @property
    def win(self):  # Windows file stem
        return SLOTS[self.name][1]


def still(body):
    return [(body, 0)]
