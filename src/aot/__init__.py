"""Attack on Titan cursor theme."""

from common import ARROW_OUT, PLUS, QMARK, badge
from cursor import HOLD, ZOOM, Cursor, still
from svg import outlined, place, pulse, rot

from .art import (BLADE_TF, GREEN, blade, colossal_wall, eren_bust, flip, goggles, grapple, nape_sight, notebook, odm_move,
                  pure_titan, quill, reach, slashes, tether, thunder_spear, walls)

NAME, TITLE = "AttackOnTitan", "Attack on Titan"  # theme folder / name shown in settings

# frames ---------------------------------------------------------------------------------------------------------------

PTR_HOT, BADGE_AT = BLADE_TF[:2], (16, 47)
POINTER = [(blade(), 2400)] + [(blade(glint=g), 35) for g in range(40, -6, -6)]  # a shine runs down the blade
PTR = POINTER[0][0]
WORKING = [(PTR + place(flip(a), *BADGE_AT, .42), 60) for a in range(0, 360, 20)]  # a little Wings of Freedom spinning
BUSY = [(flip(a), 400 if a == 0 else 50) for a in range(0, 360, 15)]
TEXT = still(thunder_spear())
OVER_WALL = [(colossal_wall(r), 70) for r in (30, 22, 15, 9, 5, 2, 0.5)] + [(colossal_wall(0), HOLD)]
DROP = [(walls(dy), 45) for dy in (-24, -16, -8, 0, -5, 0, -1.5)] + [(walls(0), HOLD)]
GRAB = [(pure_titan(.75 + .25 * pulse(i)), 110) for i in range(12)]
GRABBING = [(f'<g transform="translate(0 {1.5 * pulse(i, 6):.2f})">{pure_titan(.15 * pulse(i, 6))}</g>', 90) for i in range(12)]


def mark(glyph, at=BADGE_AT, k=1.0):
    return still(badge(PTR, glyph, at, GREEN, k))


# cursors --------------------------------------------------------------------------------------------------------------

CURSORS = [
    Cursor("left_ptr", POINTER, PTR_HOT, zoom=ZOOM),
    Cursor("right_ptr", still(f'<g transform="matrix(-1 0 0 1 64 0)">{PTR}</g>'), (64 - PTR_HOT[0], PTR_HOT[1]), zoom=ZOOM),
    Cursor("question_arrow", mark(QMARK, (19, 44), 1.45), PTR_HOT, zoom=ZOOM),
    Cursor("left_ptr_watch", WORKING, PTR_HOT, zoom=ZOOM),
    Cursor("wait", BUSY, (32, 32)),
    Cursor("crosshair", still(nape_sight()), (32, 32)),
    Cursor("xterm", TEXT, (32, 32), zoom=ZOOM),
    Cursor("vertical-text", [(rot(b, 90), ms) for b, ms in TEXT], (32, 32), zoom=ZOOM),
    Cursor("pencil", still(quill()), (6, 58)),
    Cursor("crossed_circle", OVER_WALL, (32, 32)),
    Cursor("sb_v_double_arrow", still(tether(90)), (32, 32)),
    Cursor("sb_h_double_arrow", still(tether(0)), (32, 32)),
    Cursor("bd_double_arrow", still(tether(45)), (32, 32)),
    Cursor("fd_double_arrow", still(tether(-45)), (32, 32)),
    Cursor("fleur", still(odm_move()), (32, 32)),
    Cursor("sb_up_arrow", still(reach(0)), (32, 4)),
    Cursor("sb_right_arrow", still(reach(90)), (60, 32)),
    Cursor("sb_down_arrow", still(reach(180)), (32, 60)),
    Cursor("sb_left_arrow", still(reach(-90)), (4, 32)),
    Cursor("hand2", still(grapple()), (4, 4), zoom=ZOOM),
    Cursor("hand1", GRAB, (32, 32), zoom=ZOOM),
    Cursor("grabbing", GRABBING, (32, 32), zoom=ZOOM),
    Cursor("copy", mark(PLUS), PTR_HOT, zoom=ZOOM),
    Cursor("link", mark(ARROW_OUT), PTR_HOT, zoom=ZOOM),
    Cursor("context-menu", still(notebook(PTR, BADGE_AT)), PTR_HOT, zoom=ZOOM),
    Cursor("X_cursor", still(slashes()), (32, 32)),
    Cursor("zoom-in", still(goggles("+")), (24, 26)),
    Cursor("zoom-out", still(goggles("-")), (24, 26)),
    Cursor("plus", still(outlined("M10 32H54M32 10V54", "#d5dbe6", 6)), (32, 32)),
    Cursor("pin", DROP, (32, 50)),
    Cursor("person", still(eren_bust(32, 26)), (32, 32)),
]
