"""SVG plumbing: palette, shared <defs>, the shadow wrapper and small shape helpers."""

import itertools
import math
import re

OUT, WHITE = "#16171d", "#ffffff"
HAT, BAND, BONE = "#f5c443", "#d7263d", "#fbf6ea"
SKIN, NAVY, RED = "#f8c99c", "#1f3a68", "#ff4d5e"
SKIN_LIT, SKIN_SH = "#ffe3c4", "#eaa576"

_ids = itertools.count()


def _grad(id_, *stops, x2=0, y2=1):
    """Linear gradient; stops are colours spread evenly, or (offset, colour) pairs."""
    n = len(stops) - 1
    tags = "".join(
        f'<stop offset="{s[0]}" stop-color="{s[1]}"/>' if isinstance(s, tuple) else f'<stop offset="{i / n:g}" stop-color="{s}"/>'
        for i, s in enumerate(stops)
    )
    return f'<linearGradient id="{id_}" x2="{x2}" y2="{y2}">{tags}</linearGradient>'


DEFS = (
    '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
    '<feDropShadow dx="1" dy="1.5" stdDeviation="1.2" flood-opacity=".45"/></filter>'
    '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6"/></filter>'
    '<radialGradient id="glass" cx=".35" cy=".35" r=".8"><stop stop-color="#ffffff"/>'
    '<stop offset="1" stop-color="#7cc8f5"/></radialGradient>'
    '<radialGradient id="lens" cx=".4" cy=".35" r=".75"><stop stop-color="#d9ffe0" stop-opacity=".35"/>'
    '<stop offset="1" stop-color="#1e7d3a" stop-opacity=".55"/></radialGradient>'
    + _grad("gold", "#ffe28f", "#e5a21c")
    + _grad("skin", "#ffe0bf", "#eeae78", x2=1)
    + _grad("steel", "#ffffff", "#d5dbe6", "#8d97aa")
    + _grad("blackgl", "#4a4d58", (".5", "#1b1c22"))
    + _grad("hakiblade", "#3a3542", (".5", "#121016"))
    + _grad("bronze", "#d9a066", "#8a5a2b")
    + _grad("straw", "#f6d98a", "#e2b55a")
    + _grad("vest", "#e5323f", "#b81f2e")
    + _grad("meat", "#d9764a", "#8f3b20", x2=1)
)

RAW = re.compile(r"<!--raw-->(.*?)<!--/raw-->", re.S)


def raw(markup):
    """Draw `markup` underneath, without the shadow (glows). Only at the top level of a body."""
    return f"<!--raw-->{markup}<!--/raw-->"


def svg(body, view, zoom=1):
    """Full document: raw glows underneath, then the dark-outlined body with a drop shadow."""
    k = f'<g transform="scale({zoom})">'
    under = "".join(RAW.findall(body))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view * zoom:g} {view * zoom:g}"><defs>{DEFS}</defs>{k}{under}</g>'
        f'<g filter="url(#sh)" stroke="{OUT}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'
        f"{k}{RAW.sub('', body)}</g></g></svg>"
    )


# transforms -----------------------------------------------------------------------------------------------------------


def rot(body, deg, cx=32, cy=32):
    return f'<g transform="rotate({deg:.2f} {cx} {cy})">{body}</g>'


def place(body, x, y, k):
    """A 64-grid drawing centred on (x, y), scaled by k."""
    return f'<g transform="translate({x:.2f} {y:.2f}) scale({k}) translate(-32 -32)">{body}</g>'


def tfs(tf):
    """tf = (tx, ty, deg, k): translate, rotate, scale."""
    tx, ty, deg, k = tf
    return f"translate({tx} {ty}) rotate({deg}) scale({k})"


def tf_point(tf, x, y):
    tx, ty, deg, k = tf
    a = math.radians(deg)
    return tx + k * (x * math.cos(a) - y * math.sin(a)), ty + k * (x * math.sin(a) + y * math.cos(a))


# shapes ---------------------------------------------------------------------------------------------------------------


def outlined(d, color, width):
    return (
        f'<path d="{d}" fill="none" stroke-width="{width + 3}"/>'
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"/>'
    )


def ring(cx, cy, r, color, width):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke-width="{width + 3}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{width}"/>'
    )


def clipped(d, body):
    cid = f"c{next(_ids)}"
    return f'<clipPath id="{cid}"><path d="{d}"/></clipPath><g clip-path="url(#{cid})" stroke="none">{body}</g>'


def puffs(circles, fill=WHITE):
    """Cloud silhouette: outline pass, then fill pass, so overlaps merge."""
    edge = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{OUT}" stroke-width="6"/>' for x, y, r in circles)
    body = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="none"/>' for x, y, r in circles)
    return edge + body


def multi(items, tf=(0, 0, 0, 1), extra=""):
    """[(element, fill)] drawn as one silhouette: one outline pass for all, then each fill."""
    outline = "".join(e for e, _ in items)
    fills = "".join(f'<g fill="{f}" stroke="none">{e}</g>' for e, f in items)
    return f'<g transform="{tfs(tf)}"><g fill="none" stroke="{OUT}" stroke-width="{6 / tf[3]:.2f}">{outline}</g>{fills}{extra}</g>'


def cel(items, tf, extra="", off=(-1.6, -1.3)):
    """Like multi, with cel shading: [(element, (lit, shade))], each part's bottom-right rim in the shade colour."""
    cid = f"cel{next(_ids)}"
    allp = "".join(e for e, _ in items)
    return (
        f'<g transform="{tfs(tf)}"><g fill="none" stroke="{OUT}" stroke-width="{6 / tf[3]:.2f}">{allp}</g>'
        f'<clipPath id="{cid}">{allp}</clipPath>'
        + "".join(f'<g fill="{sh}" stroke="none">{e}</g>' for e, (_, sh) in items)
        + f'<g clip-path="url(#{cid})" stroke="none" transform="translate({off[0]} {off[1]})">'
        + "".join(f'<g fill="{lit}">{e}</g>' for e, (lit, _) in items) + "</g>" + extra + "</g>"
    )


# motion ---------------------------------------------------------------------------------------------------------------


def pulse(i, n=12):
    """0..1..0 over n frames."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * i / n)


def bolt(x1, y1, x2, y2, rng, n=4, jag=3.5):
    """Jagged lightning path from (x1, y1) to (x2, y2)."""
    mid = [(x1 + (x2 - x1) * i / n + rng.uniform(-jag, jag), y1 + (y2 - y1) * i / n + rng.uniform(-jag, jag)) for i in range(1, n)]
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in [(x1, y1), *mid, (x2, y2)])
