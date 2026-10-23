"""The drawings: each function returns SVG markup on a 64 grid (unless noted)."""

import math
import random

from svg import (BAND, BONE, HAT, NAVY, OUT, RED, SKIN, SKIN_LIT, SKIN_SH, WHITE, bolt, cel, clipped, multi,
                 outlined, place, pulse, puffs, raw, ring, rot, tf_point, tfs)

# small pieces ---------------------------------------------------------------------------------------------------------


def hat(x, y, k):
    """Straw hat, origin at the crown base."""
    return (
        f'<g transform="translate({x} {y}) scale({k})">'
        f'<ellipse rx="23" ry="5" fill="{HAT}"/>'
        f'<path d="M-13 0C-13-16 13-16 13 0Z" fill="{HAT}"/>'
        f'<path d="M-12.6-4.5Q0-7 12.6-4.5L13 0H-13Z" fill="{BAND}"/></g>'
    )


def bone(x1, y1, x2, y2, w=5):
    """Bone with knobbed ends."""
    nx, ny = (y2 - y1), -(x2 - x1)
    k = 3.6 / math.hypot(nx, ny)
    knobs = "".join(
        f'<circle cx="{x + s * nx * k:.1f}" cy="{y + s * ny * k:.1f}" r="4" fill="{BONE}"/>'
        for x, y in ((x1, y1), (x2, y2)) for s in (-1, 1)
    )
    return knobs + outlined(f"M{x1} {y1}L{x2} {y2}", BONE, w)


def fist(fill="url(#skin)"):
    """Fist with the knuckles at the origin, facing -x."""
    knuckles = "".join(f'<rect x="0" y="{y}" width="13" height="6" rx="3" fill="{fill}"/>' for y in (-12, -6, 0, 6))
    return (
        f'<rect x="3" y="-12" width="24" height="24" rx="9" fill="{fill}"/>' + knuckles
        + f'<rect x="9" y="6.5" width="17" height="7" rx="3.5" fill="{fill}"/>'
    )


def jolly():
    """Straw Hat Jolly Roger, centred on (32, 32)."""
    knobs = "".join(
        f'<circle cx="{x}" cy="{y}" r="4" fill="{BONE}"/>'
        for x, y in ((7, 31), (11, 27), (57, 31), (53, 27), (7, 57), (11, 61), (57, 57), (53, 61))
    )
    teeth = '<path d="M29 47V52M32 47V52M35 47V52" stroke-width="1.5"/>'
    skull = (
        f'<circle cx="32" cy="36" r="14" fill="{BONE}"/>'
        f'<rect x="25" y="42" width="14" height="11" rx="3" fill="{BONE}"/>'
        f'<circle cx="32" cy="36" r="12" fill="{BONE}" stroke="none"/>'
        f'<circle cx="26.5" cy="36" r="3.6" fill="{OUT}"/><circle cx="37.5" cy="36" r="3.6" fill="{OUT}"/>'
        f'<path d="M32 41l-1.6 2.6h3.2z" fill="{OUT}" stroke-width="1"/>' + teeth
    )
    return knobs + outlined("M9 29L55 59M55 29L9 59", BONE, 5) + skull + hat(32, 25, 1)


# busy: Gear 5 orbit ---------------------------------------------------------------------------------------------------

NIKA_CLOUD = "M-13 6C-19 2-18-7-13-9C-19-15-14-23-8-21C-9-29 0-32 3-26C6-33 15-29 13-22C19-21 20-13 15-9C20-6 18 3 13 6Z"
NIKA_CURLS = "M-9-12q3-3 6 0M3-18q3-2 6 1M-3-23q2-2 4 0M9-11q2-2 4 1"
NIKA_COLLAR = ((-7, 13.5, 3.5), (0, 15.5, 4), (7, 13.5, 3.5))


def nika():
    """Gear 5 Luffy laughing, centred on the origin."""
    bangs = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{WHITE}" stroke-width="2"/>' for x, y, r in ((-6, -8, 4.2), (6, -8, 4.2), (0, -9.5, 4.8))
    )
    face = (
        '<circle cy="2" r="11" fill="url(#skin)" stroke-width="2.5"/>' + bangs
        + '<path d="M-7.5 0q2.5-3.5 5 0M2.5 0q2.5-3.5 5 0" fill="none" stroke-width="2.2"/>'
        + '<path d="M-8 4.5Q0 6 8 4.5Q7 14 0 14Q-7 14-8 4.5Z" fill="#6b0f1a" stroke-width="2"/>'
        + f'<path d="M-7.3 5.2Q0 6.6 7.3 5.2L7 7.5Q0 8.8-7 7.5Z" fill="{WHITE}" stroke="none"/>'
        + '<ellipse cy="12" rx="4" ry="1.8" fill="#e5484d" stroke="none"/>'
        + '<path d="M3 2.6h4.5M4.3 1.7v1.8M6 1.7v1.8" stroke-width="1"/>'
    )
    hair = f'<path d="{NIKA_CLOUD}" fill="{WHITE}" stroke-width="3"/><path d="{NIKA_CURLS}" stroke="#c4cad6" stroke-width="1.3" fill="none"/>'
    return puffs(NIKA_COLLAR) + hair + face


def orbit(a, cx=32, cy=32, r=10, k=0.7):
    """Gear 5 head bouncing round (cx, cy) with a cloud trail, at angle `a`."""
    def at(deg, rr):
        return cx + rr * math.cos(math.radians(deg)), cy + rr * math.sin(math.radians(deg))

    trail = "".join(
        f'<g opacity="{op}">{puffs([(*at(a - lag, r + 2), size * k / 0.7)])}</g>'
        for lag, size, op in ((40, 4.5, 0.9), (68, 3.4, 0.6), (92, 2.4, 0.35))
    )
    x, y = at(a, r)
    wob = math.sin(math.radians(3 * a))
    head = (
        f'<g transform="translate({x:.2f} {y:.2f}) rotate({15 * math.sin(math.radians(2 * a)):.2f}) '
        f'scale({k * (1 + 0.07 * wob):.3f} {k * (1 - 0.07 * wob):.3f})">{nika()}</g>'
    )
    return trail + head


def aura_ring(cx, cy, r, i):
    """Pulsing Haki ring with a couple of sparks flying off it. Frame i of 12."""
    p, rng = pulse(i), random.Random(i)
    sparks = ""
    for a in rng.sample(range(0, 360, 30), 2):
        x, y = cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))
        sparks += bolt(x, y, x + 9 * math.cos(math.radians(a)), y + 9 * math.sin(math.radians(a)), rng, 3, 2.5)
    return (
        raw(f'<circle cx="{cx}" cy="{cy}" r="{r + 3 * p:.1f}" fill="none" stroke="#ff1f3a" stroke-width="{4 + 5 * p:.1f}" '
            f'opacity="{0.25 + 0.4 * p:.2f}" filter="url(#glow)"/>')
        + f'<path d="{sparks}" fill="none" stroke="#ff2a40" stroke-width="3"/><path d="{sparks}" fill="none" stroke="{OUT}" stroke-width="1.2"/>'
    )


# props ----------------------------------------------------------------------------------------------------------------


def compass():
    """Compass rose, north in red."""
    def point(deg, length, light, dark):
        a, w = math.radians(deg), 6 if length > 20 else 4
        tip = (32 + length * math.cos(a), 32 + length * math.sin(a))
        sides = [(32 + w * math.cos(a + s), 32 + w * math.sin(a + s)) for s in (-math.pi / 4, math.pi / 4)]
        return "".join(
            f'<polygon points="32,32 {tip[0]:.1f},{tip[1]:.1f} {x:.1f},{y:.1f}" fill="{c}" stroke-width="1.6"/>'
            for (x, y), c in zip(sides, (light, dark))
        )

    short = "".join(point(d, 17, "#f6e7b8", "#c9a44c") for d in (-45, 45, 135, 225))
    long_ = point(-90, 29, "#ff6b6b", BAND) + "".join(point(d, 29, "#e9edf5", NAVY) for d in (0, 90, 180))
    return ring(32, 32, 16, "url(#gold)", 1.6) + short + long_ + '<circle cx="32" cy="32" r="3" fill="url(#gold)" stroke-width="1.5"/>'


def scope():
    """Sogeking's sniper goggle lens."""
    lines = "M32 13V27M32 37V51M13 32H27M37 32H51"
    ticks = "".join(
        f"M{32 + 15 * math.cos(math.radians(a)):.1f} {32 + 15 * math.sin(math.radians(a)):.1f}"
        f"L{32 + 18 * math.cos(math.radians(a)):.1f} {32 + 18 * math.sin(math.radians(a)):.1f}"
        for a in range(45, 360, 90)
    )
    return (
        '<circle cx="32" cy="32" r="20" fill="url(#lens)" stroke="none"/>'
        + ring(32, 32, 21, "#6d4c2f", 4.5) + '<circle cx="32" cy="32" r="21" fill="none" stroke="url(#gold)" stroke-width="1.2"/>'
        + f'<path d="{lines}{ticks}" stroke="{WHITE}" stroke-width="3.6"/><path d="{lines}{ticks}" stroke-width="1.6"/>'
        + f'<circle cx="32" cy="32" r="2.2" fill="{BAND}" stroke-width="1.2"/>'
    )


def brush():
    """Kanjuro's ink brush, tip at (6, 58)."""
    nodes = "M30-3.2V3.2M44-3.2V3.2"
    return (
        '<g transform="translate(6 58) rotate(-45)">'
        f'<path d="M0 0Q4-5 13-4.8V4.8Q4 5 0 0Z" fill="{OUT}" stroke-width="2"/>'
        '<rect x="13" y="-4.8" width="5" height="9.6" rx="1" fill="url(#gold)" stroke-width="2"/>'
        '<rect x="18" y="-3.4" width="40" height="6.8" rx="2" fill="#c58b4a" stroke-width="2.2"/>'
        f'<path d="{nodes}" stroke="#7a4a26" stroke-width="1.4"/>'
        f'<rect x="58" y="-3.8" width="3.5" height="7.6" rx="1" fill="{BAND}" stroke-width="2"/>'
        + outlined("M61.5 0q5 2 3 9", BAND, 1.8) + "</g>"
    )


def porthole(sign):
    """Brass porthole magnifier with a rope-wrapped handle."""
    glyph = "M20 26H32" + ("M26 20V32" if sign == "+" else "")
    rivets = "".join(
        f'<circle cx="{26 + 15 * math.cos(math.radians(a)):.1f}" cy="{26 + 15 * math.sin(math.radians(a)):.1f}" r="1.3" '
        'fill="#fff3c4" stroke-width=".8"/>'
        for a in range(0, 360, 45)
    )
    return (
        outlined("M37 37L56 56", "#7a4a26", 7)
        + '<path d="M43 40.5l-3 3M47 44.5l-3 3M51 48.5l-3 3" stroke="#d8b06a" stroke-width="2"/>'
        + '<circle cx="26" cy="26" r="15" fill="url(#glass)" fill-opacity=".85"/>'
        + ring(26, 26, 15, "#c8962e", 5) + rivets
        + f'<path d="{glyph}" stroke-width="3.5"/>'
    )


def reach(deg):
    """Fist on a rubber arm pointing up, rotated by `deg`."""
    return rot(outlined("M32 18V62", SKIN, 7) + f'<g transform="translate(32 5) rotate(90) scale(.7)">{fist()}</g>', deg)


def log_pose(needle):
    """Log Pose bracelet, needle swinging to `needle` degrees."""
    a = math.radians(needle - 90)
    tip = (32 + 11 * math.cos(a), 30 + 11 * math.sin(a))
    tail = (32 - 7 * math.cos(a), 30 - 7 * math.sin(a))
    return (
        '<rect x="12" y="38" width="40" height="14" rx="7" fill="#7a4a26"/>'
        '<path d="M16 45H48" stroke="#c9995a" stroke-width="1.4" stroke-dasharray="2 2.5"/>'
        '<circle cx="32" cy="30" r="15" fill="url(#glass)"/>' + ring(32, 30, 15, "url(#gold)", 2.5)
        + f'<path d="M32 30L{tip[0]:.1f} {tip[1]:.1f}" stroke="{BAND}" stroke-width="2.6"/>'
        + f'<path d="M32 30L{tail[0]:.1f} {tail[1]:.1f}" stroke="{NAVY}" stroke-width="2.6"/>'
        + '<circle cx="32" cy="30" r="1.8" fill="url(#gold)" stroke-width="1"/>'
    )


def forbidden(deg, flash=0.0):
    """No-entry sign with the Jolly Roger shaking `deg`, red Haki `flash` behind it."""
    slash = "M15 15L49 49"
    glow = raw(f'<circle cx="32" cy="32" r="26" fill="none" stroke="#ff1f3a" stroke-width="12" opacity="{flash:.2f}" filter="url(#glow)"/>')
    return (
        (glow if flash else "")
        + f'<circle cx="32" cy="32" r="25" fill="{WHITE}" stroke-width="9"/>'
        + f'<path d="{slash}" stroke-width="9"/>'
        + f'<circle cx="32" cy="32" r="25" fill="none" stroke="{BAND}" stroke-width="5"/>'
        + f'<path d="{slash}" stroke="{BAND}" stroke-width="5"/>'
        + rot(place(jolly(), 32, 33, 0.6), deg, 32, 40)
    )


def crocodile_hook():
    """Crocodile's gold hook and ribbed cuff, with the shaft along the horizontal resize axis."""
    hook = "M27 47V26C27 14 33 7 43 8C56 9 58 25 49 32C45 35 40 33 37 29L46 26C50 23 48 17 43 17C36 16 36 23 36 29V47Z"
    shine = "M30 40V26Q30 11 42 11Q50 11 52 19"
    body = (
        f'<path d="{hook}" fill="url(#gold)" stroke-width="2.6"/>'
        + clipped(hook, f'<path d="{shine}" fill="none" stroke="#fff4c5" stroke-width="2.2"/>')
        + '<rect x="20" y="44" width="23" height="14" rx="3" fill="url(#gold)" stroke-width="2.6"/>'
        + '<path d="M24 47V55M29 47V55M34 47V55M39 47V55" stroke="#a86c16" stroke-width="1.4"/>'
        + '<path d="M22 46H41M22 56H41" stroke="#fff0b5" stroke-width="1.5"/>'
    )
    return rot(body, -90)


# swords ---------------------------------------------------------------------------------------------------------------

KATANA = "M0 0Q22-3.6 46-3.8V3.8Q24 3.4 6 2.2Z"


def sword(x, y, deg, hilt=WHITE, wrap_color="#2b2f3a"):
    """Katana with its tip at (x, y), blade heading `deg`."""
    wrap = "M51-3.8L54 3.8L57-3.8L60 3.8L63-3.8L66 3.8M51 3.8L54-3.8L57 3.8L60-3.8L63 3.8L66-3.8"
    return (
        f'<g transform="translate({x} {y}) rotate({deg:.1f})">'
        f'<path d="{KATANA}" fill="url(#steel)" stroke-width="2.4"/>'
        + clipped(KATANA, '<path d="M8 .9Q24 .2 45 .6" fill="none" stroke="#b9c2d3" stroke-width="1.2"/>')
        + '<rect x="45" y="-4.5" width="4" height="9" rx="1" fill="url(#gold)" stroke-width="2"/>'
        + '<ellipse cx="50" rx="2.4" ry="7.5" fill="url(#gold)" stroke-width="2"/>'
        + f'<rect x="52" y="-3.8" width="15" height="7.6" rx="1.5" fill="{hilt}" stroke-width="2.2"/>'
        + f'<path d="{wrap}" stroke="{wrap_color}" stroke-width="1"/>'
        + '<rect x="67" y="-4.2" width="3.5" height="8.4" rx="1.2" fill="url(#gold)" stroke-width="2"/></g>'
    )


def crossed():
    """Wado Ichimonji and Sandai Kitetsu crossed."""
    return sword(9, 8, 45) + sword(55, 8, 135, "#8b1e2d", "#f1c9a0")


# Mihawk's Yoru, drawn along +x with the tip at the origin
YORU_BLADE = "M0 0L33-5.5V5.5Z"
YORU = [
    f'<path d="{YORU_BLADE}"/>',
    '<path d="M33-13Q35-10 35-7L38-7Q38-10 40-13Q40-5 39 0Q40 5 40 13Q38 10 38 7L35 7Q35 10 33 13Q34 5 34 0Q34-5 33-13Z"/>',
    '<rect x="39" y="-2.6" width="16" height="5.2" rx="1.5"/>',
    '<path d="M54-6L60 0L54 6L52 0Z"/>',
]
YORU_TF = (5, 4, 45, 1.3)
YORU_SPARKS = [(8, -2, 0, -1), (20, -4, 0, -1), (30, -5, 0, -1), (20, 4, 0, 1), (30, 5, 0, 1), (36, -13, 0, -1), (0, 0, -1, -.3), (36, 13, .3, 1)]


def yoru(haki=False, glint=None):
    """Yoru pointing up-left; `haki` coats the blade, `glint` is a shine `glint` units down the blade."""
    items = [(YORU[0], "url(#hakiblade)" if haki else "url(#blackgl)"), (YORU[1], "url(#bronze)"), (YORU[2], "#3a2420"), (YORU[3], "url(#bronze)")]
    extra = (
        '<circle cx="36.5" r="2.2" fill="#2fae6a"/><path d="M41-2.6L44 2.6M45-2.6L48 2.6M49-2.6L52 2.6" stroke="#8a5a2b" stroke-width="1"/>'
        + (f'<path d="{YORU_BLADE}" fill="none" stroke="{RED}" stroke-width="1.3"/>' if haki
           else '<path d="M4-.4L31-2.6" stroke="#dfe5ef" stroke-width="1.4" opacity=".8"/>')
        + ("" if glint is None else
           clipped(YORU_BLADE, f'<rect x="{glint}" y="-8" width="4" height="16" fill="#fff" opacity=".8" transform="rotate(25 {glint} 0)"/>'))
    )
    return multi(items, YORU_TF, extra)


def haki_aura(parts, tf, anchors, i):
    """Haki surge round `parts` (drawn at tf): (glow underneath, red/black lightning on top). Frame i of 12."""
    p, rng = pulse(i), random.Random(i)
    glow = raw(f'<g transform="{tfs(tf)}" fill="none" stroke="#ff1f3a" stroke-width="{(8 + 14 * p) / tf[3]:.1f}" '
               f'opacity="{0.25 + 0.5 * p:.2f}" filter="url(#glow)">{"".join(parts)}</g>')
    pts = [(*tf_point(tf, x, y), *tf_point((0, 0, tf[2], 1), dx, dy)) for x, y, dx, dy in anchors]
    d = "".join(bolt(x, y, x + dx * rng.uniform(7, 12), y + dy * rng.uniform(7, 12), rng) for x, y, dx, dy in rng.sample(pts, 3))
    return glow, f'<path d="{d}" fill="none" stroke="#ff2a40" stroke-width="3.4"/><path d="{d}" fill="none" stroke="{OUT}" stroke-width="1.4"/>'


def yoru_working(i):
    glow, sparks = haki_aura([YORU[0]], YORU_TF, YORU_SPARKS, i)
    return glow + yoru(haki=True) + sparks


QMARK = "M-3.4-3a3.6 3.6 0 1 1 5.2 3.2c-1.2.7-1.8 1.5-1.8 2.9M0 6.2v.1"
PLUS = "M0-5.5V5.5M-5.5 0H5.5"
ARROW_OUT = "M-4.5 4.5L4.5-4.5M-2-4.5H4.5V2"


def badge(body, glyph, at, k=1.0):
    """`body` with a navy round badge holding `glyph` at `at`."""
    x, y = at
    return body + (
        f'<g transform="translate({x} {y}) scale({k})"><circle r="10.5" fill="{NAVY}"/>'
        f'<path d="{glyph}" fill="none" stroke="{WHITE}" stroke-width="3"/></g>'
    )


def menu_card(body, at):
    """`body` with a little wanted poster at `at`."""
    x, y = at
    return body + (
        f'<g transform="translate({x - 10} {y - 13})"><rect width="21" height="27" rx="1.5" fill="#f3e2b3" stroke-width="2.2"/>'
        '<path d="M3 4.5H18" stroke="#5a3a1a" stroke-width="2"/><rect x="4" y="7.5" width="13" height="10" fill="#d9c08a" stroke-width="1.2"/>'
        '<path d="M3 21H18M5 24H16" stroke="#5a3a1a" stroke-width="1.4"/></g>'
    )


# link: Luffy pointing -------------------------------------------------------------------------------------------------


def straw_hat(cx, cy, k):
    weave = "".join(f'<path d="M{x} -12.5Q{x * 1.1:.1f} -6 {x * 1.05:.1f} -1" stroke="#c99a45" stroke-width=".8" fill="none"/>' for x in (-8, -3, 3, 8))
    return (
        f'<g transform="translate({cx} {cy}) scale({k})">'
        '<ellipse rx="23" ry="5.5" fill="url(#straw)"/><path d="M-19 1.6Q0 6 19 1.6" stroke="#c99a45" stroke-width="1.2" fill="none"/>'
        f'<path d="M-13 0C-13-17 13-17 13 0Z" fill="url(#straw)"/>{weave}'
        f'<path d="M-12.6-4.8Q0-7.4 12.6-4.8L13 0H-13Z" fill="{BAND}"/>'
        '<path d="M-7-11Q-2-13.6 4-12.6" stroke="#fff6d8" stroke-width="1.6" fill="none" opacity=".8"/></g>'
    )


def luffy_bust(cx, cy):
    """Chibi Luffy grinning, head centred on (cx, cy), open vest with the X scar."""
    hair = (f'<path d="M{cx - 11} {cy - 7}L{cx - 14} {cy + 1}L{cx - 10} {cy - 1}L{cx - 12} {cy + 5}L{cx - 8} {cy}'
            f'L{cx + 8} {cy}L{cx + 12} {cy + 5}L{cx + 10} {cy - 1}L{cx + 14} {cy + 1}L{cx + 11} {cy - 7}Z" fill="#1b1b22" stroke-width="1.6"/>')
    bangs = (f'<path d="M{cx - 10} {cy - 6}L{cx - 8} {cy - 1}L{cx - 5.5} {cy - 5}L{cx - 3} {cy - 0.5}L{cx} {cy - 5}L{cx + 2.5} {cy - 1}'
             f'L{cx + 5} {cy - 5}L{cx + 7.5} {cy - 1}L{cx + 10} {cy - 6}V{cy - 9}H{cx - 10}Z" fill="#1b1b22" stroke="none"/>')
    face = (
        f'<circle cx="{cx}" cy="{cy}" r="10" fill="url(#skin)"/>' + bangs
        + f'<path d="M{cx - 6} {cy + .5}q2.2-3 4.4 0M{cx + 1.6} {cy + .5}q2.2-3 4.4 0" fill="none" stroke-width="1.7"/>'
        + f'<path d="M{cx - 5.2} {cy + 2.6}h3.4M{cx - 4.4} {cy + 1.8}v1.6M{cx - 3} {cy + 1.8}v1.6" stroke-width=".8"/>'
        + f'<path d="M{cx - 6} {cy + 3.6}Q{cx} {cy + 5} {cx + 6} {cy + 3.6}Q{cx + 5} {cy + 9.6} {cx} {cy + 9.6}Q{cx - 5} {cy + 9.6} {cx - 6} {cy + 3.6}Z" fill="#6b0f1a" stroke-width="1.4"/>'
        + f'<path d="M{cx - 5.4} {cy + 4.2}Q{cx} {cy + 5.5} {cx + 5.4} {cy + 4.2}L{cx + 5.1} {cy + 5.8}Q{cx} {cy + 7} {cx - 5.1} {cy + 5.8}Z" fill="{WHITE}" stroke="none"/>'
        + f'<ellipse cx="{cx}" cy="{cy + 8.4}" rx="2.8" ry="1.2" fill="#e5484d" stroke="none"/>'
        + "".join(f'<ellipse cx="{cx + dx}" cy="{cy + 3.2}" rx="1.8" ry="1" fill="#ff8a8a" opacity=".55" stroke="none"/>' for dx in (-7.4, 7.4))
    )
    torso = (
        f'<path d="M{cx - 12} {cy + 23}Q{cx - 12} {cy + 9} {cx} {cy + 9}Q{cx + 12} {cy + 9} {cx + 12} {cy + 23}Z" fill="url(#vest)"/>'
        f'<path d="M{cx - 4} {cy + 9.6}L{cx} {cy + 22}L{cx + 4} {cy + 9.6}Z" fill="url(#skin)" stroke-width="1.3"/>'
        f'<path d="M{cx - 2} {cy + 13}L{cx + 2} {cy + 17}M{cx + 2} {cy + 13}L{cx - 2} {cy + 17}" stroke="#c9775a" stroke-width="1"/>'
        + "".join(f'<circle cx="{cx - 5.5}" cy="{cy + y}" r="1" fill="#fff3d6" stroke-width=".6"/>' for y in (15, 19))
        + outlined(f"M{cx + 10} {cy + 13}Q{cx + 15} {cy + 18} {cx + 14} {cy + 23}", SKIN, 4)
    )
    return torso + hair + face + straw_hat(cx, cy - 8, 0.58)


# pointing hand seen from the back, tip at the origin: index up, the other three folded with their knuckles showing
POINT = [
    '<rect x="-4.6" y="0" width="9.2" height="28" rx="4.6"/>', '<rect x="-6" y="18" width="27" height="22" rx="7"/>',
    '<rect x="4.2" y="15" width="7.2" height="10" rx="3.6"/>', '<rect x="10.8" y="17.2" width="7" height="9.4" rx="3.5"/>',
    '<rect x="17" y="19.8" width="6.2" height="8.4" rx="3.1"/>',
    '<rect x="-9" y="25" width="7" height="13" rx="3.5" transform="rotate(-8 -5.5 31)"/>', '<rect x="-1" y="38" width="18" height="9" rx="3"/>',
]
POINT_LINES = (
    '<path d="M10.9 20V27.5M17.1 22.5V29M-2.5 26.5Q-3.8 31-2.6 36" stroke="#c98a5c" stroke-width="1.2" fill="none"/>'
    '<path d="M-2.4 1.8Q0 .6 2.4 1.8V4.4H-2.4Z" fill="#ffd9c7" stroke="#d99a7a" stroke-width=".8"/>'
    '<path d="M-1.8 6V19" stroke="#fff" stroke-width="1.8" opacity=".7"/>'
)
POINT_TIP = (20, 3)


def luffy_pointing():
    """Chibi Luffy stretching his arm up, index finger on POINT_TIP."""
    tf = (*POINT_TIP, 0, 0.6)
    wx, wy = tf_point(tf, 8, 46)
    sx, sy = 34, 53
    arm = f"M{sx} {sy}Q{(wx + sx) / 2 + 3:.1f} {(wy + sy) / 2:.1f} {wx:.1f} {wy:.1f}"
    return (
        luffy_bust(44, 44)
        + f'<path d="{arm}" fill="none" stroke-width="7.5"/><path d="{arm}" fill="none" stroke="{SKIN_SH}" stroke-width="4.5"/>'
        + f'<path d="{arm}" fill="none" stroke="{SKIN_LIT}" stroke-width="2.4" transform="translate(-.8 -.3)"/>'
        + cel([(e, (SKIN_LIT, SKIN_SH)) for e in POINT], tf, POINT_LINES)
    )


# grab: Gear 3 giant hand ----------------------------------------------------------------------------------------------

GEAR3_ARM = '<rect x="27.5" y="52" width="9" height="14" rx="3"/>'
GEAR3_OPEN = [  # palm, index, middle, ring, pinky, thumb
    '<rect x="13" y="25" width="38" height="30" rx="14"/>',
    '<rect x="11" y="5" width="10.5" height="27" rx="5.25" transform="rotate(-14 16 30)"/>',
    '<rect x="24" y="1" width="11" height="29" rx="5.5"/>',
    '<rect x="36.5" y="3" width="10.5" height="27" rx="5.25" transform="rotate(11 41 30)"/>',
    '<rect x="46.5" y="12" width="9" height="21" rx="4.5" transform="rotate(26 51 32)"/>',
    '<rect x="0" y="30" width="20" height="11" rx="5.5" transform="rotate(-35 10 35)"/>',
]
GEAR3_FIST = [  # back of the fist, four curled fingers, thumb across
    '<rect x="9" y="12" width="46" height="38" rx="15"/>',
    '<rect x="11" y="10" width="12" height="20" rx="6"/>', '<rect x="22.5" y="8" width="12" height="20" rx="6"/>',
    '<rect x="34" y="8" width="12" height="20" rx="6"/>', '<rect x="45" y="11" width="10.5" height="19" rx="5.25"/>',
    '<rect x="8" y="31" width="30" height="11.5" rx="5.75"/>',
]
PALM_LINE = '<path d="M24 44Q33 49 44 42" stroke="#c98a5c" stroke-width="1.3" fill="none"/>'


def gear3(parts, order, k, extra=""):
    """Luffy's Gear 3 giant hand on a skinny arm, inflated by k about the palm; each part outlined on its own."""
    tf = (32 * (1 - k), 30 * (1 - k), 0, k)
    drawn = "".join(cel([(parts[i], (SKIN_LIT, SKIN_SH))], tf) for i in order)
    return multi([(GEAR3_ARM, "url(#skin)")]) + drawn + f'<g transform="{tfs(tf)}">{extra}</g>'


def open_hand(k):
    return gear3(GEAR3_OPEN, (1, 2, 3, 4, 0, 5), k, PALM_LINE)


def closed_hand(k):
    return gear3(GEAR3_FIST, (0, 4, 3, 2, 1, 5), k)


# text: meat on the bone -----------------------------------------------------------------------------------------------


def meat():
    """Meat on the bone, upright."""
    knobs = [(f'<circle cx="{32 + dx}" cy="{y}" r="4.2"/>', BONE) for y in (7, 57) for dx in (-3.4, 3.4)]
    items = knobs + [
        ('<rect x="29" y="7" width="6" height="50" rx="2"/>', BONE),
        ('<path d="M32 17C43 17 46 27 45 33C44 43 38 47 32 47C26 47 20 43 19 33C18 27 21 17 32 17Z"/>', "url(#meat)"),
    ]
    return multi(items, extra='<path d="M24 26q4-5 10-6M23 35q2 4 5 5" stroke="#f4a37c" stroke-width="1.6" fill="none"/>')
