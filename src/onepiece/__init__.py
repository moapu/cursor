"""One Piece cursor theme."""

from common import ARROW_OUT, PLUS, QMARK, badge
from cursor import HOLD, ZOOM, Cursor, still
from svg import NAVY, pulse, rot

from .art import (DOUBLE, POINT_TIP, aura_ring, bone, brush, closed_hand, compass, crossed, forbidden, hat, log_pose, luffy_pointing,
                  meat, menu_card, open_hand, orbit, porthole, reach, scope, steel, yoru, yoru_working)

NAME, TITLE = "OnePiece", "One Piece"  # theme folder / name shown in settings

# frames ---------------------------------------------------------------------------------------------------------------

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
    return still(rot(steel(DOUBLE), deg))


def mark(glyph, at=BADGE_AT, k=1.0):
    return still(badge(PTR, glyph, at, NAVY, k))


# cursors --------------------------------------------------------------------------------------------------------------

CURSORS = [
    Cursor("left_ptr", POINTER, PTR_HOT, zoom=ZOOM),
    Cursor("right_ptr", still(f'<g transform="matrix(-1 0 0 1 64 0)">{PTR}</g>'), (64 - PTR_HOT[0], PTR_HOT[1]), zoom=ZOOM),
    Cursor("question_arrow", mark(QMARK, (19, 44), 1.45), PTR_HOT, zoom=ZOOM),
    Cursor("left_ptr_watch", WORKING, PTR_HOT, zoom=ZOOM),
    Cursor("wait", BUSY, (48, 48), grid=96),
    Cursor("crosshair", still(scope()), (32, 32)),
    Cursor("xterm", TEXT, (32, 32), zoom=ZOOM),
    Cursor("vertical-text", [(rot(b, 90), ms) for b, ms in TEXT], (32, 32), zoom=ZOOM),
    Cursor("pencil", still(brush()), (6, 58)),
    Cursor("crossed_circle", SHAKE, (32, 32)),
    Cursor("sb_v_double_arrow", resize(90), (32, 32)),
    Cursor("sb_h_double_arrow", resize(0), (32, 32)),
    Cursor("bd_double_arrow", resize(45), (32, 32)),
    Cursor("fd_double_arrow", resize(-45), (32, 32)),
    Cursor("fleur", still(compass()), (32, 32)),
    Cursor("sb_up_arrow", still(reach(0)), (32, 5)),
    Cursor("sb_right_arrow", still(reach(90)), (59, 32)),
    Cursor("sb_down_arrow", still(reach(180)), (32, 59)),
    Cursor("sb_left_arrow", still(reach(-90)), (5, 32)),
    Cursor("hand2", still(luffy_pointing()), POINT_TIP, zoom=2),
    Cursor("hand1", GRAB, (32, 32), zoom=ZOOM),
    Cursor("grabbing", GRABBING, (32, 32), zoom=ZOOM),
    Cursor("copy", mark(PLUS), PTR_HOT, zoom=ZOOM),
    Cursor("link", mark(ARROW_OUT), PTR_HOT, zoom=ZOOM),
    Cursor("context-menu", still(menu_card(PTR, BADGE_AT)), PTR_HOT, zoom=ZOOM),
    Cursor("X_cursor", still(crossed()), (32, 32)),
    Cursor("zoom-in", still(porthole("+")), (26, 26)),
    Cursor("zoom-out", still(porthole("-")), (26, 26)),
    Cursor("plus", still(bone(10, 32, 54, 32) + bone(32, 10, 32, 54)), (32, 32)),
    Cursor("pin", SWING, (32, 30)),
    Cursor("person", still(hat(32, 40, 1.2)), (32, 32)),
]
