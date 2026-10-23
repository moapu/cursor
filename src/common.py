"""Drawings shared by every theme: the glyph badges on the pointer."""

from svg import WHITE

QMARK = "M-3.4-3a3.6 3.6 0 1 1 5.2 3.2c-1.2.7-1.8 1.5-1.8 2.9M0 6.2v.1"
PLUS = "M0-5.5V5.5M-5.5 0H5.5"
ARROW_OUT = "M-4.5 4.5L4.5-4.5M-2-4.5H4.5V2"


def badge(body, glyph, at, color, k=1.0):
    """`body` with a round `color` badge holding `glyph` at `at`."""
    x, y = at
    return body + (
        f'<g transform="translate({x} {y}) scale({k})"><circle r="10.5" fill="{color}"/>'
        f'<path d="{glyph}" fill="none" stroke="{WHITE}" stroke-width="3"/></g>'
    )
