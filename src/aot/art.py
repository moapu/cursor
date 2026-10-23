"""The drawings: each function returns SVG markup on a 64 grid."""

import math

from svg import BAND, OUT, WHITE, cel, clipped, multi, outlined, place, raw, ring, rot

GREEN, BROWN, HAIR = "#2f6b4a", "#5a3a22", "#3b2416"
IRON, WIRE, MUSCLE_LINE = "#646c7a", "#a7afbd", "#7f1d14"
TITAN = ("#f6d0b4", "#cf8f6e")  # (lit, shade)
STONE = ("#ddd5c3", "#b3a88f")

# ODM blade --------------------------------------------------------------------------------------------------------------

# ultrahard steel blade, drawn along +x with the chisel tip at the origin, then the ODM trigger grip
BLADE = "M0 0L10-7H40V0Z"
ODM = [
    f'<path d="{BLADE}"/>',
    '<rect x="39" y="-10" width="8" height="13" rx="2"/>',
    '<path d="M49 0C49 5 51 7.5 55.5 7.5L56.5 0Z"/>',
    '<rect x="46" y="-8" width="16" height="9" rx="3.5"/>',
]
BLADE_TF = (5, 4, 50, 1.2)


def blade(tf=BLADE_TF, glint=None):
    """ODM sword: blade with its snap-off segment lines, trigger grip; `glint` is a shine `glint` units down the blade."""
    items = [(ODM[0], "url(#steel)"), (ODM[1], IRON), (ODM[2], IRON), (ODM[3], "#2f343f")]
    extra = (
        '<path d="M9 0L19-7M18 0L28-7M27 0L37-7" stroke="#8d97aa" stroke-width="1"/>'
        + clipped(BLADE, '<path d="M3-1H40" stroke="#fff" stroke-width="1.6"/>')
        + '<circle cx="43" cy="-3.5" r="1.4" fill="#d5dbe6" stroke-width=".8"/>'
        + '<path d="M50-8V1M54-8V1M58-8V1" stroke="#4b5260" stroke-width="1"/>'
        + ("" if glint is None else
           clipped(BLADE, f'<rect x="{glint}" y="-9" width="4" height="12" fill="#fff" opacity=".9" transform="rotate(25 {glint} 0)"/>'))
    )
    return multi(items, tf, extra)


def slashes():
    """Two red blade cuts crossed, as on a titan's nape."""
    cut = "M10 8Q34 30 56 56Q30 36 10 8Z"
    return f'<path d="{cut}" fill="{BAND}" stroke-width="2.4"/><path d="{cut}" fill="{BAND}" stroke-width="2.4" transform="matrix(-1 0 0 1 64 0)"/>'


def nape_sight():
    """Four blade tips closing in on a red point, inside a dashed ring."""
    tips = "".join(multi([(f'<path d="{BLADE}"/>', "url(#steel)")], (32 + 5 * math.cos(math.radians(a)), 32 + 5 * math.sin(math.radians(a)), a, .5))
                   for a in (45, 135, 225, 315))
    return (
        f'<circle cx="32" cy="32" r="24" fill="none" stroke="{WHITE}" stroke-width="3.4"/>'
        '<circle cx="32" cy="32" r="24" fill="none" stroke-width="1.6" stroke-dasharray="5 3.4"/>'
        + tips + f'<circle cx="32" cy="32" r="2.4" fill="{BAND}" stroke-width="1.2"/>'
    )


# busy: Wings of Freedom -------------------------------------------------------------------------------------------------

SHIELD = "M13 8H51Q52 22 50 36Q47 51 32 58Q17 51 14 36Q12 22 13 8Z"
WING = "M29 50C26 38 29 22 40 11L41.5 19L46 15L45.5 23.5L50.5 22L47 30.5L50 31.5L45 38L47 40.5L38 45.5Z"
FEATHERS = "M30.5 45L40.5 21M32.5 46L44.5 25.5M34.5 46L46.5 32.5M36.5 46L45.5 39.5"


def wings_of_freedom():
    """Survey Corps emblem: white wing behind, blue wing in front, on a shield."""
    def wing(tf, fill, line):
        lines = f'<path d="{FEATHERS}" stroke="{line}" stroke-width="1.1"/>'
        return f'<g transform="{tf}"><path d="{WING}" fill="{fill}" stroke-width="2"/>{clipped(WING, lines)}</g>'

    return (
        f'<path d="{SHIELD}" fill="url(#parchment)"/>'
        + clipped(SHIELD, '<path d="M16 11H48" stroke="#fff" stroke-width="2" opacity=".7"/>')
        + wing("matrix(-1 0 0 1 61 0)", WHITE, "#aab4c4") + wing("translate(1.5 0)", "url(#wing)", "#173a78")
    )


def flip(a):
    """The emblem spun `a` degrees about its vertical axis, like a tossed coin."""
    sx = max(0.06, abs(math.cos(math.radians(a))))
    return f'<g transform="translate(32 0) scale({sx:.3f} 1) translate(-32 0)">{wings_of_freedom()}</g>'


# props ----------------------------------------------------------------------------------------------------------------


def thunder_spear():
    """Thunder spear standing upright: warhead, brass bands, tube, exhaust."""
    items = [
        ('<path d="M32 4L37.5 14V20H26.5V14Z"/>', "url(#steel)"),
        ('<rect x="27.5" y="22" width="9" height="28" rx="1.5"/>', "url(#spear)"),
        ('<rect x="26" y="19.5" width="12" height="3.5" rx="1"/>', "url(#gold)"),
        ('<rect x="26" y="35" width="12" height="3.5" rx="1"/>', "url(#gold)"),
        ('<path d="M28 49.5H36L39.5 59H24.5Z"/>', "#2f343f"),
    ]
    return multi(items, extra='<path d="M30 24V34M30 40V48" stroke="#c3cad6" stroke-width="1.4" opacity=".8"/>'
                              '<path d="M30 9L32 5.5" stroke="#fff" stroke-width="1.4"/>')




def quill():
    """Armin's quill, nib at (6, 58)."""
    barbs = "M22-1L28-8M30-1.3L36-9M38-1.5L44-9M46-1.7L52-8M24 .5L30 4.5M34 .2L40 4.4M44-.2L50 3.3"
    return (
        '<g transform="translate(6 58) rotate(-45)">'
        '<path d="M14 0Q22-10 42-10Q56-9 64-2L62 0Q54 3 42 5Q26 6 14 0Z" fill="#fbfbf7" stroke-width="2"/>'
        f'<path d="{barbs}" stroke="#c9cfd8" stroke-width="1"/>'
        '<path d="M8 0L66-1.6" stroke="#b9a27a" stroke-width="1.4"/>'
        '<path d="M0 0L8-2.4L10 0L8 2.4Z" fill="#2b2f3a" stroke-width="1.6"/></g>'
    )


def goggles(sign):
    """Hange's goggles, the left lens magnifying with `sign` in it."""
    glyph = "M18 26H30" + ("M24 20V32" if sign == "+" else "")
    rivets = "".join(
        f'<circle cx="{24 + 13 * math.cos(math.radians(a)):.1f}" cy="{26 + 13 * math.sin(math.radians(a)):.1f}" r="1.2" '
        'fill="#fff3c4" stroke-width=".8"/>'
        for a in range(0, 360, 45)
    )
    return (
        outlined("M3 36Q18 30 22 30M44 34Q54 30 62 22", BROWN, 5)
        + '<circle cx="47" cy="31" r="10" fill="url(#glass)" fill-opacity=".85"/>' + ring(47, 31, 10, "#8a5a2b", 4)
        + outlined("M36 28Q37 25 39 26", "#8a5a2b", 3)
        + '<circle cx="24" cy="26" r="13" fill="url(#glass)" fill-opacity=".85"/>' + ring(24, 26, 13, "#8a5a2b", 5) + rivets
        + f'<path d="{glyph}" stroke-width="3.5"/>'
    )


def notebook(body, at):
    """`body` with Hange's field journal at `at`."""
    x, y = at
    return body + (
        f'<g transform="translate({x - 10} {y - 13})"><rect width="21" height="27" rx="2" fill="#6b4226" stroke-width="2.2"/>'
        '<rect x="3.5" y="2.5" width="15.5" height="22" rx="1" fill="url(#parchment)" stroke-width="1.2"/>'
        '<path d="M6 8H16M6 12H16M6 16H13M6 20H16" stroke="#8a7a5a" stroke-width="1.2"/>'
        f'<path d="M13.5 0V8L15.5 6.3L17.5 8V0Z" fill="{BAND}" stroke-width="1"/></g>'
    )


# ODM gear: anchors, wires, the gear wheel -----------------------------------------------------------------------------


def anchor(x, y, deg, k=1.35):
    """ODM grappling anchor with its tip at (x, y), pointing `deg` (0 = up)."""
    return (f'<g transform="translate({x} {y}) rotate({deg}) scale({k})">'
            '<path d="M0 0L6 8L3 7.5L5 11L1.8 9.5V14H-1.8V9.5L-5 11L-3 7.5L-6 8Z" fill="url(#steel)" stroke-width="2"/></g>')


def cog():
    """ODM gear wheel, centred on (32, 32)."""
    teeth = "".join(rot('<rect x="29" y="19.5" width="6" height="6" rx="1.2"/>', a) for a in range(0, 360, 45))
    return multi([(teeth + '<circle cx="32" cy="32" r="9.5"/>', "url(#steel)")],
                 extra=f'<circle cx="32" cy="32" r="3.4" fill="{IRON}" stroke-width="1.5"/>')


def reach(deg):
    """Anchor flying up on its wire, rotated by `deg`."""
    return rot(outlined("M32 20V62", WIRE, 3.4) + anchor(32, 4, 0), deg)


def tether(deg):
    """Wire with an anchor at each end (resize), rotated by `deg`."""
    return rot(outlined("M20 32H44", WIRE, 3.4) + anchor(4, 32, -90) + anchor(60, 32, 90), deg)


def odm_move():
    """Gear wheel firing anchors in all four directions."""
    wires = "".join(rot(outlined("M32 21V12", WIRE, 2), a) for a in range(0, 360, 90))
    return wires + "".join(rot(anchor(32, 3, 0, 1), a) for a in range(0, 360, 90)) + cog()


def grapple():
    """Anchor shot up-left, its wire whipping back to the gear wheel (link)."""
    wire = "M19 19C26 40 36 22 44 40"
    return outlined(wire, WIRE, 2.6) + place(cog(), 47, 47, .55) + anchor(4, 4, -45, 1.5)


def walls(dy=None):
    """Walls Maria, Rose and Sina from above; `dy` drops a red pin onto Shiganshina from `dy` above."""
    cx, cy = 32, 28
    land = "".join(f'<circle cx="{cx + x}" cy="{cy + y}" r="{r}"/>' for x, y, r in
                   ((0, 0, 22), (0, 22, 4.5), (0, -22, 4.5), (22, 0, 4.5), (-22, 0, 4.5)))
    inner = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#8a8172" stroke-width="2"/>'
        + "".join(f'<circle cx="{cx + r * math.cos(math.radians(a)):.1f}" cy="{cy + r * math.sin(math.radians(a)):.1f}" '
                  f'r="{d}" fill="#efe2bf" stroke="#8a8172" stroke-width="1.4"/>' for a in range(0, 360, 90))
        for r, d in ((14, 3), (6.5, 2))
    )
    out = multi([(land, "url(#parchment)")], extra=inner)
    if dy is None:
        return out
    shadow = raw(f'<ellipse cx="32" cy="50" rx="{4 - dy / 10:.1f}" ry="1.6" fill="#000" opacity="{.35 + dy / 80:.2f}"/>')
    pin = (
        f'<g transform="translate(32 {50 + dy})"><path d="M0 0V-12" stroke-width="4.4"/><path d="M0 0V-12" stroke="#d5dbe6" stroke-width="2"/>'
        f'<circle cy="-15" r="5.5" fill="{BAND}" stroke-width="2.4"/><circle cx="-1.8" cy="-16.8" r="1.6" fill="#fff" stroke="none" opacity=".8"/></g>'
    )
    return shadow + out + pin


# not allowed: the Colossal Titan looks over the Wall ------------------------------------------------------------------


def colossal():
    """The Colossal Titan's skinless face, centred on (32, 32)."""
    teeth = "".join(f"M{x:.1f} 41V49" for x in (22.5, 25.7, 28.9, 32.1, 35.3, 38.5, 41.7))
    return (
        '<path d="M32 8C46 8 50 20 49 32C48 44 42 54 32 56C22 54 16 44 15 32C14 20 18 8 32 8Z" fill="url(#muscle)"/>'
        f'<path d="M22 14Q20 24 22 31M42 14Q44 24 42 31M28 10Q27 17 29 23M36 10Q37 17 35 23M18 37Q19 45 22 50M46 37Q45 45 42 50" '
        f'stroke="{MUSCLE_LINE}" stroke-width="1.4" fill="none"/>'
        '<ellipse cx="25" cy="30.5" rx="4.4" ry="3" fill="#3a0d08" stroke-width="1.4"/><ellipse cx="39" cy="30.5" rx="4.4" ry="3" fill="#3a0d08" stroke-width="1.4"/>'
        '<circle cx="25.5" cy="30.5" r="1.3" fill="#fff" stroke="none"/><circle cx="38.5" cy="30.5" r="1.3" fill="#fff" stroke="none"/>'
        '<path d="M19 27Q24 23 30 28M34 28Q40 23 45 27" stroke-width="2.6" fill="none"/>'
        f'<path d="M30 36Q32 38.5 34 36" stroke="{MUSCLE_LINE}" stroke-width="1.4" fill="none"/>'
        f'<rect x="19.5" y="40.5" width="25" height="9" rx="3" fill="#f4ecd6" stroke-width="2"/>'
        f'<path d="{teeth}M19.5 45H44.5" stroke="#b5a98a" stroke-width="1"/>'
    )


WALL = ['<rect x="2" y="37" width="60" height="6" rx="1.5"/>', '<rect x="5" y="42" width="54" height="19"/>']
BRICKS = "M5 49H59M5 55H59M15 43V49M31 43V49M47 43V49M23 49V55M39 49V55M55 49V55M15 55V61M31 55V61M47 55V61"
NO_SIGN = (f'<g transform="translate(51 51)"><circle r="9" fill="{WHITE}" stroke-width="6"/><path d="M-6-6L6 6" stroke-width="6"/>'
           f'<circle r="9" fill="none" stroke="{BAND}" stroke-width="3.2"/><path d="M-6-6L6 6" stroke="{BAND}" stroke-width="3.2"/></g>')


def colossal_wall(rise):
    """The Colossal Titan, `rise` units short of peering over the Wall, steaming; a no-entry sign on the wall."""
    steam = raw(f'<g fill="#fff" opacity="{.8 - rise / 40:.2f}" filter="url(#glow)">'
                + "".join(f'<circle cx="{x}" cy="{y + rise}" r="{r}"/>' for x, y, r in ((12, 24, 6), (52, 22, 6), (16, 12, 4.5), (49, 10, 4.5)))
                + "</g>")
    head = place(colossal(), 32, 27 + rise, .82)
    wall = cel([(e, STONE) for e in WALL], (0, 0, 0, 1), f'<path d="{BRICKS}" stroke="#9e937d" stroke-width="1"/>')
    return steam + head + wall + NO_SIGN


# grab: a Pure Titan's grin --------------------------------------------------------------------------------------------


def pure_titan(gape):
    """Smiling Pure Titan, blank-eyed; `gape` 0 grins with the teeth shut, 1 opens wide to bite."""
    d = 6 + 9 * gape
    mouth = f"M14 40Q32 44 50 40Q32 {44 + 2 * d:.1f} 14 40Z"
    inside = (
        f'<ellipse cx="32" cy="{42 + d * .9:.1f}" rx="8" ry="{2 + 2 * gape:.1f}" fill="#d9475a"/>'
        f'<path d="M14 40Q32 44 50 40" fill="none" stroke="#fff" stroke-width="6.4" stroke-dasharray="2.8 .7"/>'
        f'<path d="M14 40Q32 {44 + 2 * d:.1f} 50 40" fill="none" stroke="#fff" stroke-width="6.4" stroke-dasharray="2.8 .7"/>'
    )
    face = (
        f'<path d="M11 30Q9 9 32 9Q55 9 53 30Q50 20 42 19Q36 22 32 18Q28 22 22 19Q14 20 11 30Z" fill="{HAIR}" stroke-width="2"/>'
        f'<ellipse cx="24" cy="29" rx="4.2" ry="3.3" fill="{WHITE}" stroke-width="1.4"/><ellipse cx="40" cy="29" rx="4.2" ry="3.3" fill="{WHITE}" stroke-width="1.4"/>'
        '<circle cx="23" cy="28.6" r="1.4" fill="#1b1b22" stroke="none"/><circle cx="41.5" cy="29.8" r="1.4" fill="#1b1b22" stroke="none"/>'
        f'<path d="M20 33.5q4 1.4 8 0M36 33.5q4 1.4 8 0M30 36.5q2 1.4 4 0" stroke="{TITAN[1]}" stroke-width="1.2" fill="none"/>'
        f'<path d="{mouth}" fill="#4a0d12" stroke-width="2.2"/>' + clipped(mouth, inside)
        + f'<path d="{mouth}" fill="none" stroke-width="1.8"/>'
    )
    head = '<ellipse cx="32" cy="35" rx="20.5" ry="24"/>'
    ears = '<ellipse cx="11.5" cy="34" rx="4.5" ry="6.5"/><ellipse cx="52.5" cy="34" rx="4.5" ry="6.5"/>'
    return cel([(ears, TITAN), (head, TITAN)], (0, 0, 0, 1), face)


# person: Eren ---------------------------------------------------------------------------------------------------------


def eren_bust(cx, cy):
    """Chibi Eren glaring, head centred on (cx, cy), in his Survey Corps cloak."""
    back = f'<path d="M{cx - 11} {cy - 3}Q{cx - 13} {cy + 8} {cx - 9} {cy + 9}H{cx + 9}Q{cx + 13} {cy + 8} {cx + 11} {cy - 3}Z" fill="{HAIR}" stroke-width="1.6"/>'
    bangs = (f'<path d="M{cx - 11} {cy - 1}Q{cx - 12} {cy - 12} {cx} {cy - 12}Q{cx + 12} {cy - 12} {cx + 11} {cy - 1}L{cx + 8.5} {cy - 4}'
             f'L{cx + 6.5} {cy + .5}L{cx + 3.5} {cy - 5}L{cx + .5} {cy - 1.5}L{cx - 2.5} {cy - 5.5}L{cx - 5.5} {cy}L{cx - 8} {cy - 4.5}Z" '
             f'fill="{HAIR}" stroke-width="1.6"/>')
    eyes = "".join(
        f'<ellipse cx="{cx + dx}" cy="{cy + 1.8}" rx="2.4" ry="1.9" fill="{WHITE}" stroke-width=".9"/>'
        f'<circle cx="{cx + dx * .9}" cy="{cy + 1.9}" r="1.4" fill="#2e9e6a" stroke="none"/><circle cx="{cx + dx * .9}" cy="{cy + 1.9}" r=".6" fill="{OUT}" stroke="none"/>'
        for dx in (-4.2, 4.2)
    )
    face = (
        f'<circle cx="{cx}" cy="{cy}" r="10" fill="url(#skin)"/>' + eyes
        + f'<path d="M{cx - 7.2} {cy - 2.2}L{cx - 1.8} {cy - .2}M{cx + 7.2} {cy - 2.2}L{cx + 1.8} {cy - .2}" stroke-width="1.6"/>'
        + f'<path d="M{cx - 2.6} {cy + 5.6}Q{cx} {cy + 4.8} {cx + 2.6} {cy + 5.6}Q{cx + 2} {cy + 8.6} {cx} {cy + 8.6}Q{cx - 2} {cy + 8.6} {cx - 2.6} {cy + 5.6}Z" '
          'fill="#6b0f1a" stroke-width="1.2"/>'
        + f'<path d="M{cx - 2.2} {cy + 5.8}Q{cx} {cy + 5.2} {cx + 2.2} {cy + 5.8}V{cy + 6.6}H{cx - 2.2}Z" fill="{WHITE}" stroke="none"/>'
        + bangs
    )
    torso = (
        f'<path d="M{cx - 13} {cy + 23}Q{cx - 13} {cy + 9} {cx} {cy + 9}Q{cx + 13} {cy + 9} {cx + 13} {cy + 23}Z" fill="url(#cloak)"/>'
        f'<path d="M{cx - 6.5} {cy + 23}L{cx - 4.5} {cy + 10.5}H{cx + 4.5}L{cx + 6.5} {cy + 23}Z" fill="url(#jacket)" stroke-width="1.4"/>'
        f'<path d="M{cx - 3} {cy + 10.5}L{cx} {cy + 15.5}L{cx + 3} {cy + 10.5}Z" fill="{WHITE}" stroke-width="1.2"/>'
        f'<path d="M{cx - 5} {cy + 17}L{cx + 5.6} {cy + 21}M{cx + 5} {cy + 17}L{cx - 5.6} {cy + 21}" stroke="{BROWN}" stroke-width="1.4"/>'
        f'<ellipse cx="{cx}" cy="{cy + 10}" rx="9" ry="3" fill="url(#cloak)" stroke-width="1.6"/>'
    )
    return torso + back + face
