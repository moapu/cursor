"""One Piece cursor theme: XCursor for Linux, .cur/.ani + install.inf for Windows.

nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
"""

import io
import itertools
import math
import random
import re
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
X_DIR = ROOT / "Luffy"
WIN_DIR = ROOT / "Luffy-Windows"
X_SIZES = (24, 32, 48, 64, 96)
WIN_SIZES = (32, 48, 64, 96)
GRID = 64
HOLD = 3_600_000  # ms; cursors always loop, so a 1h last frame makes an animation play once

OUT, WHITE = "#16171d", "#ffffff"
HAT, BAND, BONE = "#f5c443", "#d7263d", "#fbf6ea"
SKIN, WOOD, NAVY = "#f8c99c", "#8a5a2b", "#1f3a68"

_ids = itertools.count()


@dataclass
class Cursor:
    name: str
    frames: list  # [(svg body, delay ms)]
    hot: tuple  # in `grid` units
    aliases: str | None = ""  # None: Windows only
    win: str | None = None  # Windows file stem
    grid: int = GRID  # > 64: drawn past the nominal box on Linux
    win_view: int = GRID  # Windows viewBox: GRID crops the top-left of a bigger grid, `grid` scales it all down
    win_frames: list | None = None  # Windows override, drawn on `win_view`
    zoom: float = 1  # Linux only: drawn this much bigger (Windows cursors are a fixed size)


def still(body):
    return [(body, 0)]


# drawing helpers ------------------------------------------------------------------------------------------------------

DEFS = (
    '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
    '<feDropShadow dx="1" dy="1.5" stdDeviation="1.2" flood-opacity=".45"/></filter>'
    '<linearGradient id="gold" x2="0" y2="1"><stop stop-color="#ffe28f"/><stop offset="1" stop-color="#e5a21c"/>'
    "</linearGradient>"
    '<linearGradient id="skin" x2="1" y2="1"><stop stop-color="#ffe0bf"/><stop offset="1" stop-color="#eeae78"/>'
    "</linearGradient>"
    '<linearGradient id="steel" x2="0" y2="1"><stop stop-color="#ffffff"/><stop offset=".5" stop-color="#d5dbe6"/>'
    '<stop offset="1" stop-color="#8d97aa"/></linearGradient>'
    '<linearGradient id="glove" x2="1" y2="1"><stop stop-color="#ffffff"/><stop offset="1" stop-color="#cfd4e2"/>'
    "</linearGradient>"
    '<radialGradient id="glass" cx=".35" cy=".35" r=".8"><stop stop-color="#ffffff"/>'
    '<stop offset="1" stop-color="#7cc8f5"/></radialGradient>'
    '<radialGradient id="lens" cx=".4" cy=".35" r=".75"><stop stop-color="#d9ffe0" stop-opacity=".35"/>'
    '<stop offset="1" stop-color="#1e7d3a" stop-opacity=".55"/></radialGradient>'
    '<radialGradient id="ember"><stop stop-color="#fff3b0"/><stop offset=".5" stop-color="#ff8a1f"/>'
    '<stop offset="1" stop-color="#d4290f"/></radialGradient>'
    '<linearGradient id="straw" x2="0" y2="1"><stop stop-color="#ffe08a"/><stop offset="1" stop-color="#f0b429"/>'
    "</linearGradient>"
    '<filter id="stk" x="-20%" y="-20%" width="140%" height="140%">'
    '<feMorphology in="SourceAlpha" operator="dilate" radius="2.2" result="d"/><feFlood flood-color="#fff"/>'
    '<feComposite in2="d" operator="in" result="w"/><feMerge><feMergeNode in="w"/><feMergeNode in="SourceGraphic"/></feMerge>'
    "</filter>"
)


EDGE = True  # white sticker edge round every cursor


RAW = re.compile(r"<!--raw-->(.*?)<!--/raw-->", re.S)


def raw(markup):
    """Draw `markup` underneath, without the sticker edge or shadow (glows). Only at the top level of a body."""
    return f"<!--raw-->{markup}<!--/raw-->"


def svg(body, view, zoom=1):
    edge = ' filter="url(#stk)"' if EDGE else ""
    k = f'<g transform="scale({zoom})">'
    under = "".join(RAW.findall(body))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view * zoom:g} {view * zoom:g}"><defs>{DEFS}</defs>{k}{under}</g>'
        f'<g filter="url(#sh)" stroke="{OUT}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'
        f"<g{edge}>{k}{RAW.sub('', body)}</g></g></g></svg>"
    )


def rot(body, deg, cx=32, cy=32):
    return f'<g transform="rotate({deg:.2f} {cx} {cy})">{body}</g>'


def place(body, x, y, k):
    return f'<g transform="translate({x:.2f} {y:.2f}) scale({k}) translate(-32 -32)">{body}</g>'


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


def finger(x, y, w, h, fill="url(#skin)"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w / 2}" fill="{fill}"/>'


def puffs(circles, fill=WHITE):
    """Cloud silhouette: outline pass, then fill pass, so overlaps merge."""
    edge = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{OUT}" stroke-width="6"/>' for x, y, r in circles)
    body = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="none"/>' for x, y, r in circles)
    return edge + body


def star(r, n=10, inner=0.55):
    pts = ((r if i % 2 == 0 else r * inner, math.pi * i / n) for i in range(2 * n))
    return " ".join(f"{d * math.cos(a):.1f},{d * math.sin(a):.1f}" for d, a in pts)


def sparkle(x, y, r):
    """Four-point glint."""
    return f'<polygon transform="translate({x} {y})" points="{star(r, 4, 0.25)}" fill="{WHITE}" stroke-width="1.2"/>'


def wave(x0, x1, amp, n=4):
    """Horizontal line from x0 to x1, wiggling `amp` either side."""
    step = (x1 - x0) / n
    return f"M{x0:.1f} 0" + (f"q{step / 2:.1f} {-amp} {step:.1f} 0" + f"t{step:.1f} 0" * (n - 1) if amp else f"H{x1:.1f}")


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


def fist_shape(fill="url(#skin)"):
    """Fist with the knuckles at the origin, facing -x."""
    knuckles = "".join(f'<rect x="0" y="{y}" width="13" height="6" rx="3" fill="{fill}"/>' for y in (-12, -6, 0, 6))
    return (
        f'<rect x="3" y="-12" width="24" height="24" rx="9" fill="{fill}"/>' + knuckles
        + f'<rect x="9" y="6.5" width="17" height="7" rx="3.5" fill="{fill}"/>'
    )


# characters -----------------------------------------------------------------------------------------------------------


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


NIKA_CLOUD = "M-13 6C-19 2-18-7-13-9C-19-15-14-23-8-21C-9-29 0-32 3-26C6-33 15-29 13-22C19-21 20-13 15-9C20-6 18 3 13 6Z"
NIKA_CURLS = "M-9-12q3-3 6 0M3-18q3-2 6 1M-3-23q2-2 4 0M9-11q2-2 4 1"
NIKA_HAIR = (
    (-13, -4, 5.5), (-11, -13, 7), (-3, -18, 8), (7, -17, 7.5), (13, -9, 6.5),
    (-15, -23, 5.5), (-6, -28, 6), (5, -29, 5.5), (14, -21, 5), (-11, -35, 4), (0, -38, 4), (11, -33, 3.5),
    (-17, -41, 2.5), (6, -45, 2.5),
)
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


def chopper(tilt=0, bob=0):
    """Chopper wondering, centred on (32, 34)."""
    antler = "M19 21L9 11M13 15L6 16M12 14L12 7"
    mirror = "M45 21L55 11M51 15L58 16M52 14L52 7"
    face = (
        '<circle cx="32" cy="35" r="13" fill="#a0612f"/>'
        '<ellipse cx="32" cy="41" rx="8.5" ry="6" fill="#f6dcc0" stroke-width="1.5"/>'
        '<ellipse cx="32" cy="37" rx="3.6" ry="2.6" fill="#3a6fd8" stroke-width="1.5"/>'
        f'<ellipse cx="25.5" cy="31" rx="2.4" ry="3" fill="{OUT}" stroke="none"/>'
        f'<ellipse cx="38.5" cy="31" rx="2.4" ry="3" fill="{OUT}" stroke="none"/>'
        f'<circle cx="26.3" cy="30" r=".9" fill="{WHITE}" stroke="none"/><circle cx="39.3" cy="30" r=".9" fill="{WHITE}" stroke="none"/>'
        '<path d="M29.5 43.5q2.5 2 5 0" fill="none" stroke-width="1.5"/>'
    )
    cap = (
        '<path d="M20 22V11Q20 5 32 5Q44 5 44 11V22Z" fill="#f48fb1"/>'
        '<ellipse cx="32" cy="22" rx="17" ry="4" fill="#f48fb1"/>'
        f'<path d="M28.5 10.5L35.5 17.5M35.5 10.5L28.5 17.5" stroke="{WHITE}" stroke-width="3"/>'
    )
    bubble = (
        f'<g transform="translate(0 {bob})"><circle cx="52" cy="40" r="9" fill="{WHITE}"/>'
        '<path d="M48.6 37.3a3.6 3.6 0 1 1 5.2 3.2c-1.2.7-1.8 1.5-1.8 2.9M52 46.2v.1" fill="none" stroke-width="2.6"/></g>'
    )
    return rot(outlined(antler, "#8b5a2b", 3) + outlined(mirror, "#8b5a2b", 3) + face + cap, tilt, 32, 42) + bubble


# props ----------------------------------------------------------------------------------------------------------------

KATANA_TIP = (5, 4)
BLADE = "M0 0Q22-3.6 46-3.8V3.8Q24 3.4 6 2.2Z"


def katana(glint=None, ting=0):
    """Zoro's Wado Ichimonji, tip (the hotspot) at KATANA_TIP; `glint` slides a shine along the blade."""
    shine = "" if glint is None else f'<ellipse cx="{glint}" rx="4" ry="8" fill="{WHITE}" opacity=".95"/>'
    wrap = "M51-3.8L54 3.8L57-3.8L60 3.8L63-3.8L66 3.8M51 3.8L54-3.8L57 3.8L60-3.8L63 3.8L66-3.8"
    body = (
        f'<path d="{BLADE}" fill="url(#steel)" stroke-width="2.4"/>'
        + clipped(BLADE, '<path d="M8 .9Q24 .2 45 .6" fill="none" stroke="#b9c2d3" stroke-width="1.2"/>' + shine)
        + '<rect x="45" y="-4.5" width="4" height="9" rx="1" fill="url(#gold)" stroke-width="2"/>'
        + '<ellipse cx="50" rx="2.4" ry="7.5" fill="url(#gold)" stroke-width="2"/>'
        + f'<rect x="52" y="-3.8" width="15" height="7.6" rx="1.5" fill="{WHITE}" stroke-width="2.2"/>'
        + f'<path d="{wrap}" stroke="#2b2f3a" stroke-width="1"/>'
        + '<rect x="67" y="-4.2" width="3.5" height="8.4" rx="1.2" fill="url(#gold)" stroke-width="2"/>'
    )
    return (
        f'<g transform="translate({KATANA_TIP[0]} {KATANA_TIP[1]}) rotate(45)">{body}</g>'
        + (sparkle(*KATANA_TIP, ting) if ting else "")
    )


def cigarette(phase):
    """Sanji's cigarette, ember pulsing, smoke curling up."""
    t = math.radians(phase)
    smoke = "M32 11" + "".join(f"L{32 + 3.2 * math.sin(i / 2.2 + t) * i / 11:.1f} {11 - i}" for i in range(1, 12))
    glow = 0.25 + 0.2 * math.sin(t)
    return (
        f'<path d="{smoke}" fill="none" stroke="#c9ceda" stroke-width="2.4" opacity=".85"/>'
        + f'<circle cx="32" cy="13" r="6" fill="#ff7a2f" opacity="{glow:.2f}" stroke="none"/>'
        + f'<rect x="29" y="13" width="6" height="40" rx="1.5" fill="{WHITE}" stroke-width="2.4"/>'
        + '<rect x="29" y="44" width="6" height="9" rx="1.5" fill="#e8a65a" stroke-width="2.4"/>'
        + '<path d="M30.5 47h1M33 49h1M30.8 51h1" stroke="#b9772f" stroke-width="1"/>'
        + '<rect x="29" y="11" width="6" height="4" rx="1.5" fill="url(#ember)" stroke-width="2"/>'
    )


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


def glove(closed, bob):
    """Buggy's Bara Bara hand: a detached white glove floating."""
    cuff = (
        '<rect x="19" y="50" width="27" height="7" rx="3" fill="#2f5bd3"/>'
        f'<path d="M21 53.5H44" stroke="{BAND}" stroke-width="2.4"/>'
        '<path d="M22 61h4M30 61.5h5M39 61h4" stroke-width="2" opacity=".55"/>'
    )
    if closed:
        hand = (
            '<rect x="14" y="22" width="36" height="28" rx="10" fill="url(#glove)"/>'
            + "".join(finger(x, 17, 9, 13, "url(#glove)") for x in (14.5, 23.5, 32.5, 41.5))
            + '<rect x="13" y="33" width="25" height="9" rx="4.5" fill="url(#glove)"/>'
        )
    else:
        hand = (
            '<rect x="8" y="27" width="9" height="18" rx="4.5" transform="rotate(-40 12 36)" fill="url(#glove)"/>'
            + finger(17, 13, 7.5, 24, "url(#glove)") + finger(25, 8, 7.5, 28, "url(#glove)")
            + finger(33, 9, 7.5, 27, "url(#glove)") + finger(41, 15, 7, 22, "url(#glove)")
            + '<rect x="16" y="28" width="33" height="24" rx="10" fill="url(#glove)"/>'
            + '<path d="M27 37V45M32.5 36V45M38 37V45" stroke="#b9bfd0" stroke-width="1.4"/>'
        )
    return f'<g transform="translate(0 {bob})">{hand}{cuff}</g>'


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
    return rot(outlined("M32 18V62", SKIN, 7) + f'<g transform="translate(32 5) rotate(90) scale(.7)">{fist_shape()}</g>', deg)


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
    slash = "M15 15L49 49"
    return (
        (raw(f'<circle cx="32" cy="32" r="26" fill="none" stroke="#ff1f3a" stroke-width="12" opacity="{flash:.2f}" filter="url(#glow)"/>')
         if flash else "")
        + f'<circle cx="32" cy="32" r="25" fill="{WHITE}" stroke-width="9"/>'
        + f'<path d="{slash}" stroke-width="9"/>'
        + f'<circle cx="32" cy="32" r="25" fill="none" stroke="{BAND}" stroke-width="5"/>'
        + f'<path d="{slash}" stroke="{BAND}" stroke-width="5"/>'
        + rot(place(jolly(), 32, 33, 0.6), deg, 32, 40)
    )


# Gum-Gum Pistol -------------------------------------------------------------------------------------------------------

TARGET = (26, 24)  # where the knuckles land: the hotspot, 128 grid


def punch(x, coil=0, width=11, burst=0, burst_op=1.0, speed=False):
    """Fist `x` units back from the target along the arm, which comes in from the bottom-right."""
    gid, mid = f"g{next(_ids)}", f"m{next(_ids)}"
    path = f"M{x + 20} 0" + (f"q6 {-coil} 12 0" + "t12 0" * 18 if coil else "H260")
    fade = (
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x + 30}" x2="{x + 95}" y2="0">'
        f'<stop stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-60" y="-80" width="400" height="160">'
        f'<rect x="-60" y="-80" width="400" height="160" fill="url(#{gid})"/></mask>'
    )
    lines = f"M{x + 34} -21H{x + 80}M{x + 44} 22H{x + 90}M{x + 56} -30H{x + 84}"
    rays = "".join(
        f"M{-burst * 0.8 * math.cos(math.radians(a)):.1f} {burst * 0.8 * math.sin(math.radians(a)):.1f}"
        f"L{-burst * 1.15 * math.cos(math.radians(a)):.1f} {burst * 1.15 * math.sin(math.radians(a)):.1f}"
        for a in (-50, -25, 0, 25, 50)
    )
    return (
        f'<g transform="translate({TARGET[0]} {TARGET[1]}) rotate(45) scale(1.4)">'
        + (f'<g opacity="{burst_op}" transform="translate({-burst * 0.45:.1f} 0)"><polygon points="{star(burst)}" fill="#ffd23f" stroke-width="2.5"/>'
           f'<polygon points="{star(burst * 0.55)}" fill="{WHITE}" stroke="none"/></g>' if burst else "")
        + fade + f'<g mask="url(#{mid})">{outlined(path, SKIN, width)}'
        + (f'<path d="{lines}" stroke-width="2.2" opacity=".7"/>' if speed else "") + "</g>"
        + f'<g transform="translate({x} 0) scale(1.35)">{fist_shape()}</g>'
        + (f'<g opacity="{burst_op}"><path d="{rays}" stroke-width="4.5"/><path d="{rays}" stroke="{WHITE}" stroke-width="2"/></g>'
           if burst else "")
        + "</g>"
    )


PUNCH = [
    (punch(28, width=12), 40),
    (punch(40, coil=4, width=13), 70),
    (punch(46, coil=6, width=14), 80),
    (punch(24, width=8, speed=True), 25),
    (punch(8, width=7, speed=True), 25),
    (punch(-3, width=8, burst=10), 50),
    (punch(-1, width=9, burst=14), 70),
    (punch(1, width=10, burst=15, burst_op=0.4), 60),
    (punch(1, width=10), HOLD),
]


# pointer options ------------------------------------------------------------------------------------------------------

ARROW = "M7 4V47L17 38.5L24.5 54.5L32 51.5L24.8 36H38Z"
DOUBLE = "M4 32L17 19V27H47V19L60 32L47 45V37H17V45Z"
FIRE_DEFS = (
    '<linearGradient id="fire" x2="1" y2="1"><stop stop-color="#fff6c2"/><stop offset=".45" stop-color="#ffb22e"/>'
    '<stop offset="1" stop-color="#f0441c"/></linearGradient>'
    '<linearGradient id="haki" x2="0" y2="1"><stop stop-color="#4a4656"/><stop offset=".45" stop-color="#16141c"/>'
    '<stop offset="1" stop-color="#050407"/></linearGradient>'
    '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6"/></filter>'
)
DEFS += FIRE_DEFS


def tongue(bx, by, deg, length, width=3.6):
    """Flame licking from (bx, by) towards `deg`."""
    a = math.radians(deg)
    dx, dy, px, py = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    tip = (bx + dx * length, by + dy * length)
    c1 = (bx + dx * length * 0.55 + px * width * 1.2, by + dy * length * 0.55 + py * width * 1.2)
    c2 = (bx + dx * length * 0.45 - px * width * 0.6, by + dy * length * 0.45 - py * width * 0.6)
    shape = (
        f"M{bx + px * width:.1f} {by + py * width:.1f}Q{c1[0]:.1f} {c1[1]:.1f} {tip[0]:.1f} {tip[1]:.1f}"
        f"Q{c2[0]:.1f} {c2[1]:.1f} {bx - px * width:.1f} {by - py * width:.1f}Z"
    )
    core = (bx + dx * length * 0.55, by + dy * length * 0.55)
    return (
        f'<path d="{shape}" fill="url(#fire)" stroke-width="1.6"/>'
        f'<path d="M{bx + px * width * 0.45:.1f} {by + py * width * 0.45:.1f}L{core[0]:.1f} {core[1]:.1f}'
        f'L{bx - px * width * 0.45:.1f} {by - py * width * 0.45:.1f}Z" fill="#fff2a8" stroke="none"/>'
    )


FLAME_BASES = ((18, 15.5), (25, 22.5), (32, 29.5), (30, 36), (28, 43), (28, 53))


def fire_arrow(phase):
    """Ace's Fire Fist: the arrow is ablaze, flames trailing like a comet."""
    t = math.radians(phase)
    flames = "".join(
        tongue(x, y, 45 + 14 * math.sin(t + i * 1.7), 17 + 6 * math.sin(t * 2 + i * 2.3), 4.6)
        for i, (x, y) in enumerate(FLAME_BASES)
    )
    embers = "".join(
        f'<circle cx="{42 + 9 * ((phase / 360 + i / 3) % 1) + 3 * i:.1f}" cy="{44 + 9 * ((phase / 360 + i / 3) % 1) - 4 * i:.1f}" '
        f'r="{1.4 - 0.9 * ((phase / 360 + i / 3) % 1):.2f}" fill="#ffb22e" stroke="none"/>'
        for i in range(3)
    )
    return flames + embers + f'<path d="{ARROW}" fill="url(#fire)"/>' + clipped(ARROW, f'<path d="M9 8V38" stroke="{WHITE}" stroke-width="2.5" opacity=".7"/>')


def bolt(x1, y1, x2, y2, rng, n=4, jag=3.5):
    pts = [(x1, y1)] + [
        (x1 + (x2 - x1) * i / n + rng.uniform(-jag, jag), y1 + (y2 - y1) * i / n + rng.uniform(-jag, jag)) for i in range(1, n)
    ] + [(x2, y2)]
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def haki(d, anchors=(), seed=0, arcs=True, glow=0.55):
    """Conqueror's Haki coating: black gloss, red rim and glow, black-and-red lightning crackling off `anchors`."""
    rng = random.Random(seed)
    bolts = "".join(
        bolt(x, y, x + dx * rng.uniform(7, 12), y + dy * rng.uniform(7, 12), rng)
        for x, y, dx, dy in rng.sample(list(anchors), 3)
    ) if arcs and anchors else ""
    return (
        raw(f'<path d="{d}" fill="none" stroke="#ff1f3a" stroke-width="7" opacity="{glow:.2f}" filter="url(#glow)"/>')
        + (f'<path d="{bolts}" fill="none" stroke="#ff2a40" stroke-width="3.4"/><path d="{bolts}" fill="none" stroke="{OUT}" stroke-width="1.4"/>' if bolts else "")
        + f'<path d="{d}" fill="none" stroke-width="5"/><path d="{d}" fill="url(#haki)" stroke="#ff4d5e" stroke-width="1.6"/>'
        + clipped(d, f'<path d="M10 10V40" stroke="{WHITE}" stroke-width="2.4" opacity=".35"/>')
    )


ARROW_SPARKS = [(14, 12, 0.7, -0.7), (24, 22, 0.7, -0.7), (34, 32, 0.8, -0.5), (36, 37, 0.6, 0.8), (30, 50, 0.9, 0.4),
                (7, 30, -1, 0), (7, 44, -1, 0.3), (22, 54, -0.6, 0.8)]
RED = "#ff4d5e"


def clean(d, band=False, sheen=None, rim=1.0, tip=False, emblem=None, edge=RED):
    """Haki clean: black gloss with a red rim. Options: hat band, sliding sheen, rim brightness, red-dipped tip, emblem."""
    gid = f"t{next(_ids)}"
    dip = (
        f'<linearGradient id="{gid}" x2="1" y2="1"><stop stop-color="{BAND}"/><stop offset=".3" stop-color="#7a1020"/>'
        '<stop offset=".55" stop-color="#16141c"/><stop offset="1" stop-color="#050407"/></linearGradient>'
    ) if tip else ""
    inside = (
        (f'<rect y="24" width="64" height="5" fill="{BAND}"/>' if band else "")
        + f'<path d="M10 10V40" stroke="{WHITE}" stroke-width="2.4" opacity=".35"/>'
        + ("" if sheen is None else
           f'<rect x="{sheen}" y="-20" width="7" height="110" fill="{RED}" opacity=".55" transform="rotate(25 {sheen} 30)"/>')
        + (emblem or "")
    )
    return (
        dip + f'<path d="{d}" fill="none" stroke-width="5"/>'
        + f'<path d="{d}" fill="url(#{gid if tip else "haki"})" stroke="{edge}" stroke-width="1.6" stroke-opacity="{rim:.2f}"/>'
        + clipped(d, inside)
    )


def pulse(i, n=12):
    """0..1..0 over n frames."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * i / n)


def surge(d, anchors, i):
    """Haki building up: the aura swells and lightning crackles."""
    p = pulse(i)
    return (
        raw(f'<path d="{d}" fill="none" stroke="#ff1f3a" stroke-width="{8 + 14 * p:.1f}" opacity="{0.25 + 0.5 * p:.2f}" filter="url(#glow)"/>')
        + haki(d, anchors, i, glow=0.3 + 0.5 * p)
    )


def aura_ring(cx, cy, r, i):
    """Pulsing Haki ring with a couple of sparks flying off it."""
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


IBEAM_SPARKS = [(22, 8, -0.7, -0.7), (42, 8, 0.7, -0.7), (22, 56, -0.7, 0.7), (42, 56, 0.7, 0.7), (29, 30, -1, 0),
                (35, 34, 1, 0), (35, 20, 1, 0), (29, 45, -1, 0)]
DOUBLE_SPARKS = [(10, 26, -0.5, -0.9), (10, 38, -0.5, 0.9), (32, 27, 0, -1), (32, 37, 0, 1), (54, 26, 0.5, -0.9),
                 (54, 38, 0.5, 0.9), (22, 27, 0.2, -1), (42, 37, -0.2, 1)]


def zeus(phase):
    """Nami's Zeus: a thundercloud with a face firing a bolt at the tip."""
    t = math.radians(phase)
    bob = 1.2 * math.sin(t)
    flash = phase % 120 < 40
    path = "M6 4L21 20L16 23L31 35L26 38L38 45"
    cloud = puffs([(40, 46 + bob, 7), (49, 43 + bob, 8), (56, 49 + bob, 6.5), (46, 53 + bob, 7), (37, 53 + bob, 5.5)], "#6b7487")
    face = (
        f'<ellipse cx="44" cy="{47.5 + bob:.1f}" rx="1.6" ry="2" fill="{WHITE}" stroke="none"/>'
        f'<ellipse cx="51" cy="{47.5 + bob:.1f}" rx="1.6" ry="2" fill="{WHITE}" stroke="none"/>'
        f'<path d="M45 {52 + bob:.1f}q2.5 2 5 0" fill="none" stroke="{WHITE}" stroke-width="1.4"/>'
    )
    return (
        (f'<path d="{path}" fill="none" stroke="#fff27a" stroke-width="9" opacity=".5" filter="url(#glow)"/>' if flash else "")
        + outlined(path, "#ffd23f", 4.2) + f'<path d="{path}" fill="none" stroke="{WHITE}" stroke-width="1.4"/>'
        + cloud + face
    )


# help options ---------------------------------------------------------------------------------------------------------

QMARK = "M-3.4-3a3.6 3.6 0 1 1 5.2 3.2c-1.2.7-1.8 1.5-1.8 2.9M0 6.2v.1"


def qmark(x, y, k=1.0):
    return (
        f'<g transform="translate({x} {y}) scale({k})"><path d="{QMARK}" fill="none" stroke-width="5.5"/>'
        f'<path d="{QMARK}" fill="none" stroke="{HAT}" stroke-width="2.6"/></g>'
    )


def den_den(shake=0, ring_lines=False):
    """Den Den Mushi ringing (purupuru)."""
    green, shell = "#b8de7a", "#e8743b"
    holes = "".join(
        f'<circle cx="{40 + 4.6 * math.cos(math.radians(a)):.1f}" cy="{36 + 4.6 * math.sin(math.radians(a)):.1f}" r="1" fill="{OUT}" stroke="none"/>'
        for a in range(0, 360, 45)
    )
    body = (
        f'<rect x="8" y="44" width="48" height="10" rx="5" fill="{green}"/>'
        + f'<path d="M11 50Q6 36 13 28Q20 23 25 30L27 46Z" fill="{green}"/>'
        + outlined("M14 28L10 17M20 27L21 15", green, 2.6)
        + "".join(
            f'<circle cx="{x}" cy="{y}" r="3.6" fill="{WHITE}" stroke-width="2"/><circle cx="{x}" cy="{y + 0.8}" r="1.5" fill="{OUT}" stroke="none"/>'
            f'<path d="M{x - 3.4} {y - 0.4}Q{x} {y - 2.2} {x + 3.4} {y - 0.4}" fill="{green}" stroke-width="1.4"/>'
            for x, y in ((10, 15), (21, 13))
        )
        + '<path d="M16 37q3 1.5 6 0" fill="none" stroke-width="1.5"/>'
        + f'<circle cx="40" cy="36" r="13" fill="{shell}"/>'
        + f'<circle cx="40" cy="36" r="7" fill="{BONE}" stroke-width="2"/>' + holes
        + outlined("M31 23Q40 15 49 23", "#2b2f3a", 3.4)
        + '<rect x="27" y="20" width="7" height="6" rx="2" fill="#2b2f3a" stroke-width="2"/>'
        + '<rect x="46" y="20" width="7" height="6" rx="2" fill="#2b2f3a" stroke-width="2"/>'
    )
    lines = '<path d="M24 12q-2 4 0 8M56 12q2 4 0 8M58 30q3 3 2 7" fill="none" stroke-width="2"/>' if ring_lines else ""
    return rot(body, shake, 32, 50) + lines + qmark(55, 9)


def luffy_huh(pops):
    """Luffy blanking out, question marks popping one after another."""
    face = (
        '<path d="M17 30L15 38L20 34ZM47 30L49 38L44 34Z" fill="#1b1b1b" stroke-width="1.5"/>'
        '<circle cx="32" cy="38" r="15" fill="url(#skin)"/>'
        '<path d="M19 29L22 35L25 29L28 35L31 29L34 35L37 29L40 35L43 29L45 33V27H19Z" fill="#1b1b1b" stroke="none"/>'
        f'<circle cx="26" cy="38" r="1.9" fill="{OUT}" stroke="none"/><circle cx="38" cy="38" r="1.9" fill="{OUT}" stroke="none"/>'
        '<path d="M23 33.5h5M36 33.5h5" stroke-width="1.4"/>'
        '<path d="M36 42.5h4M37.3 41.6v1.8M38.8 41.6v1.8" stroke-width="1"/>'
        f'<ellipse cx="32" cy="47" rx="2.2" ry="2.6" fill="#6b0f1a" stroke-width="1.4"/>'
    )
    marks = "".join(qmark(x, y, k) for (x, y, k), shown in zip(((48, 14, 0.9), (56, 7, 0.7), (40, 6, 0.6)), pops) if shown)
    return face + hat(32, 27, 0.95) + marks


# resize options -------------------------------------------------------------------------------------------------------


def sea_king(phase):
    """Sea King swimming: head and forked tail are the two arrowheads; horizontal."""
    t = math.radians(phase)
    y = lambda x: 3 * math.sin(x / 6 + t)
    body = "M-20 {:.1f}".format(y(-20)) + "".join(f"L{x} {y(x):.1f}" for x in range(-18, 16, 2))
    hy, ty = y(14), y(-20)
    fin, skin, belly = "#7b5cff", "#3fb39a", "#bfe9d8"
    head = (
        f'<g transform="translate(14 {hy:.1f})">'
        f'<path d="M-2-3L3-10L7-5L11-9L12-3Z" fill="{fin}" stroke-width="1.6"/>'
        f'<path d="M-2-6Q9-9 17-2L11 1L17 3Q9 9-2 6Z" fill="{skin}" stroke-width="2.2"/>'
        f'<path d="M12 1.2l1.2 1.4 1.2-1.4" fill="{WHITE}" stroke-width=".8"/>'
        f'<circle cx="5" cy="-2.6" r="2" fill="{WHITE}" stroke-width="1.2"/><circle cx="5.5" cy="-2.6" r="1" fill="{OUT}" stroke="none"/></g>'
    )
    tail = f'<g transform="translate(-20 {ty:.1f})"><path d="M2 0L-9-8L-6 0L-9 8Z" fill="{fin}" stroke-width="2"/></g>'
    return (
        '<g transform="translate(32 32)">' + tail
        + f'<path d="{body}" fill="none" stroke-width="10"/><path d="{body}" fill="none" stroke="{skin}" stroke-width="7"/>'
        + f'<path d="{body}" fill="none" stroke="{belly}" stroke-width="2" transform="translate(0 1.6)"/>'
        + head + "</g>"
    )


def fire_double(phase):
    t = math.radians(phase)
    flames = "".join(
        tongue(x, 27, -90 + 12 * math.sin(t + i * 1.9), 12 + 5 * math.sin(t * 2 + i * 2.1), 4)
        for i, x in enumerate((14, 23, 32, 41, 50))
    )
    return flames + f'<path d="{DOUBLE}" fill="url(#fire)"/>'


# swords ---------------------------------------------------------------------------------------------------------------


def sword(x, y, deg, hilt=WHITE, wrap_color="#2b2f3a"):
    """Katana with its tip at (x, y), blade heading `deg`."""
    wrap = "M51-3.8L54 3.8L57-3.8L60 3.8L63-3.8L66 3.8M51 3.8L54-3.8L57 3.8L60-3.8L63 3.8L66-3.8"
    return (
        f'<g transform="translate({x} {y}) rotate({deg:.1f})">'
        f'<path d="{BLADE}" fill="url(#steel)" stroke-width="2.4"/>'
        + clipped(BLADE, '<path d="M8 .9Q24 .2 45 .6" fill="none" stroke="#b9c2d3" stroke-width="1.2"/>')
        + '<rect x="45" y="-4.5" width="4" height="9" rx="1" fill="url(#gold)" stroke-width="2"/>'
        + '<ellipse cx="50" rx="2.4" ry="7.5" fill="url(#gold)" stroke-width="2"/>'
        + f'<rect x="52" y="-3.8" width="15" height="7.6" rx="1.5" fill="{hilt}" stroke-width="2.2"/>'
        + f'<path d="{wrap}" stroke="{wrap_color}" stroke-width="1"/>'
        + '<rect x="67" y="-4.2" width="3.5" height="8.4" rx="1.2" fill="url(#gold)" stroke-width="2"/></g>'
    )


def crossed(spread=0, spark=0):
    """Wado Ichimonji and Sandai Kitetsu crossed; `spread` opens them, `spark` flashes where they meet."""
    return (
        rot(sword(9, 8, 45), -spread)
        + rot(sword(55, 8, 135, "#8b1e2d", "#f1c9a0"), spread)
        + (f'<polygon transform="translate(32 31)" points="{star(spark, 8, 0.4)}" fill="#ffe28f" stroke-width="1.6"/>' if spark else "")
    )


def clash(spread, spark):
    return (
        '<circle cx="32" cy="32" r="27" fill="none" stroke-width="9"/>'
        + f'<circle cx="32" cy="32" r="27" fill="none" stroke="{BAND}" stroke-width="5"/>'
        + crossed(spread, spark)
    )


CLASH = [(clash(0, 0), 1500), (clash(26, 0), 50), (clash(12, 0), 40), (clash(0, 10), 60), (clash(0, 6), 60)]


# sticker set --------------------------------------------------------------------------------------------------------

IBEAM = "M22 8H42V13H35V51H42V56H22V51H29V13H22Z"


# body top, body bottom, band
STICKERS = {
    "white-red": ("#ffffff", "#dfe3ec", BAND),
    "luffy-red": ("#ff5a5f", "#c8102e", "#ffffff"),
    "denim": ("#4f7fe0", "#1f3f8f", BAND),
    "jolly-black": ("#4a4d5a", "#121318", BAND),
    "nika": ("#ffffff", "#ddd2ff", "#8a6cff"),
    "sea": ("#5fd6e8", "#1677b8", "#ffffff"),
    "zoro-green": ("#5cc46a", "#1f7a3a", OUT),
    "gomu-purple": ("#a77bf0", "#5b2fb0", "#ffffff"),
}
STICKER = "white-red"


def sticker(d, band=True, sheen=None, colors=None):
    """Two-tone sticker shape with a hat band and a dark outline."""
    top, bottom, band_color = colors or STICKERS[STICKER]
    gid = f"s{next(_ids)}"
    fill = f'<linearGradient id="{gid}" x2="0" y2="1"><stop stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>'
    extra = (f'<rect y="24" width="64" height="7" fill="{band_color}"/>' if band else "") + (
        "" if sheen is None else
        f'<rect x="{sheen}" y="-20" width="8" height="110" fill="{WHITE}" opacity=".55" transform="rotate(25 {sheen} 30)"/>'
    )
    return fill + f'<path d="{d}" fill="url(#{gid})"/>' + clipped(d, extra) + f'<path d="{d}" fill="none"/>'


def gomu_fruit():
    """Gomu Gomu no Mi; the stem tip at (6, 5) points."""
    swirl = "M33 40a4 4 0 1 1 5 4M44 34a4 4 0 1 1 5 4M45 50a4 4 0 1 1 5 4M34 52a3.5 3.5 0 1 1 4.5 3.5"
    return (
        outlined("M30 30Q20 14 6 5", "#3d7a2a", 2.6)
        + '<path d="M18 16Q26 8 31 15Q24 21 18 16Z" fill="#5fb84a" stroke-width="1.8"/>'
        + '<circle cx="42" cy="45" r="16" fill="#8e5bd6"/>'
        + f'<path d="{swirl}" fill="none" stroke="#4a2386" stroke-width="2"/>'
    )


def chibi_point():
    """Chibi Luffy, arm stretched, fingertip at (6, 5)."""
    face = (
        '<path d="M33 42L31 50L36 46ZM55 42L57 50L52 46Z" fill="#1b1b1b" stroke-width="1.4"/>'
        '<circle cx="44" cy="48" r="12" fill="url(#skin)"/>'
        '<path d="M34 41L36 46L39 41L41 46L44 41L46 46L49 41L51 46L54 41V38H34Z" fill="#1b1b1b" stroke="none"/>'
        '<path d="M38.5 47q2-2.6 4 0M45.5 47q2-2.6 4 0" fill="none" stroke-width="1.8"/>'
        '<path d="M37.5 51Q44 52.5 50.5 51Q49.5 58 44 58Q38.5 58 37.5 51Z" fill="#6b0f1a" stroke-width="1.6"/>'
        f'<path d="M38.2 51.6Q44 52.8 49.8 51.6L49.5 53Q44 54.2 38.5 53Z" fill="{WHITE}" stroke="none"/>'
    )
    return (
        outlined("M36 50Q26 34 13 12", SKIN, 4.5) + '<circle cx="14" cy="13" r="4.6" fill="url(#skin)"/>'
        + outlined("M13 12L6 5", SKIN, 3) + face + hat(44, 39, 0.62)
    )


def poneglyph(glow):
    """Road Poneglyph with a glowing question mark."""
    glyphs = "".join(f"M{x} {y}h3M{x + 1.5} {y - 1.5}v3" for y in (25, 30, 47, 52) for x in (15, 21, 27, 33, 39))
    return (
        '<path d="M12 20L22 12H54L44 20Z" fill="#a23c3c"/>'
        '<path d="M44 20L54 12V50L44 58Z" fill="#5a1d1d"/>'
        '<rect x="12" y="20" width="32" height="38" fill="#7d2b2b"/>'
        f'<path d="{glyphs}" stroke="#d79a7a" stroke-width="1.2"/>'
        f'<circle cx="28" cy="39" r="9" fill="#ffd23f" opacity="{glow:.2f}" filter="url(#glow)" stroke="none"/>'
        + qmark(28, 39, 1.4)
    )


# natural colours: Yoru, Luffy pointing -------------------------------------------------------------------------------

STEEL = "#b8c2d4"
SKIN_LIT, SKIN_SH = "#ffe3c4", "#eaa576"
DEFS += (
    '<linearGradient id="blackgl" x2="0" y2="1"><stop stop-color="#4a4d58"/><stop offset=".5" stop-color="#1b1c22"/></linearGradient>'
    '<linearGradient id="bronze" x2="0" y2="1"><stop stop-color="#d9a066"/><stop offset="1" stop-color="#8a5a2b"/></linearGradient>'
    '<linearGradient id="hakiblade" x2="0" y2="1"><stop stop-color="#3a3542"/><stop offset=".5" stop-color="#121016"/></linearGradient>'
    '<linearGradient id="straw2" x2="0" y2="1"><stop stop-color="#f6d98a"/><stop offset="1" stop-color="#e2b55a"/></linearGradient>'
    '<linearGradient id="vest" x2="0" y2="1"><stop stop-color="#e5323f"/><stop offset="1" stop-color="#b81f2e"/></linearGradient>'
)


def tfs(tf):
    """tf = (tx, ty, deg, k): translate, rotate, scale."""
    tx, ty, deg, k = tf
    return f"translate({tx} {ty}) rotate({deg}) scale({k})"


def tf_point(tf, x, y):
    tx, ty, deg, k = tf
    a = math.radians(deg)
    return tx + k * (x * math.cos(a) - y * math.sin(a)), ty + k * (x * math.sin(a) + y * math.cos(a))


def multi(items, tf=(0, 0, 0, 1), extra=""):
    """[(element, fill)] drawn as one sticker: one outline pass for all, then each fill."""
    k = tf[3]
    outline = "".join(e for e, _ in items)
    fills = "".join(f'<g fill="{f}" stroke="none">{e}</g>' for e, f in items)
    return f'<g transform="{tfs(tf)}"><g fill="none" stroke="{OUT}" stroke-width="{6 / k:.2f}">{outline}</g>{fills}{extra}</g>'


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


def haki_aura(parts, tf, anchors, i):
    """Haki surge round `parts` (drawn at tf): (glow underneath, red/black lightning on top). Frame i of 12."""
    p, rng = pulse(i), random.Random(i)
    glow = raw(f'<g transform="{tfs(tf)}" fill="none" stroke="#ff1f3a" stroke-width="{(8 + 14 * p) / tf[3]:.1f}" '
               f'opacity="{0.25 + 0.5 * p:.2f}" filter="url(#glow)">{"".join(parts)}</g>')
    pts = []
    for x, y, dx, dy in anchors:
        px, py = tf_point(tf, x, y)
        ox, oy = tf_point((0, 0, tf[2], 1), dx, dy)
        pts.append((px, py, ox, oy))
    d = "".join(bolt(x, y, x + dx * rng.uniform(7, 12), y + dy * rng.uniform(7, 12), rng) for x, y, dx, dy in rng.sample(pts, 3))
    return glow, f'<path d="{d}" fill="none" stroke="#ff2a40" stroke-width="3.4"/><path d="{d}" fill="none" stroke="{OUT}" stroke-width="1.4"/>'


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


def yoru_working(i):
    glow, sparks = haki_aura([YORU[0]], YORU_TF, YORU_SPARKS, i)
    return glow + yoru(haki=True) + sparks


def straw_hat(cx, cy, k):
    weave = "".join(f'<path d="M{x} -12.5Q{x * 1.1:.1f} -6 {x * 1.05:.1f} -1" stroke="#c99a45" stroke-width=".8" fill="none"/>' for x in (-8, -3, 3, 8))
    return (
        f'<g transform="translate({cx} {cy}) scale({k})">'
        '<ellipse rx="23" ry="5.5" fill="url(#straw2)"/><path d="M-19 1.6Q0 6 19 1.6" stroke="#c99a45" stroke-width="1.2" fill="none"/>'
        f'<path d="M-13 0C-13-17 13-17 13 0Z" fill="url(#straw2)"/>{weave}'
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


# Enma standing on its tip (text), Gear 3 giant hand (grab) ------------------------------------------------------------

DEFS += (
    '<linearGradient id="enmablk" x2="0" y2="1"><stop stop-color="#5a5f66"/><stop offset=".35" stop-color="#15171b"/><stop offset="1" stop-color="#050506"/></linearGradient>'
    '<linearGradient id="enmapurple" x2="0" y2="1"><stop stop-color="#b07ad6"/><stop offset=".45" stop-color="#7a3fa6"/><stop offset="1" stop-color="#4a2266"/></linearGradient>'
    '<linearGradient id="gold2" x2="0" y2="1"><stop stop-color="#ffe7a3"/><stop offset=".5" stop-color="#e2b54a"/><stop offset="1" stop-color="#a87a22"/></linearGradient>'
)
ENMA_BLADE = "M0 0Q28-4 56-4.2V4.2Q30 3.8 6 2.4Z"
ENMA_HAMON = "M3 1.9" + "".join(f"Q{x + 2} {0.6 if i % 2 else 2.8} {x + 4} 1.7" for i, x in enumerate(range(3, 55, 4))) + "L56 4.4L4 4.4Z"
ENMA_TF = (32, 62, -90, 0.73)  # tip down, hilt up


def enma(shine=None):
    """Enma: black blade with the mint hamon, round gold tsuba, purple hilt. `shine` runs down the blade."""
    items = [
        (f'<path d="{ENMA_BLADE}"/>', "url(#enmablk)"), ('<rect x="55" y="-4.8" width="4" height="9.6" rx="1"/>', "url(#gold2)"),
        ('<ellipse cx="60.6" rx="2.6" ry="10"/>', "url(#gold2)"), ('<rect x="62.5" y="-4.2" width="18" height="8.4" rx="2"/>', "url(#enmapurple)"),
        ('<rect x="80" y="-4.6" width="3.6" height="9.2" rx="1.4"/>', "url(#gold2)"),
    ]
    extra = (
        clipped(ENMA_BLADE, f'<path d="{ENMA_HAMON}" fill="#9ef0d2"/>' + ("" if shine is None else
                f'<rect x="{shine}" y="-8" width="4" height="16" fill="#fff" opacity=".8" transform="rotate(25 {shine} 0)"/>'))
        + '<path d="M6-1.2Q30-2.6 54-2.8" stroke="#8a9099" stroke-width=".9" fill="none" opacity=".8"/>'
        '<path d="M64-2.2H79" stroke="#e7c8ff" stroke-width="1.4" opacity=".7"/><path d="M60.6-8V8" stroke="#a87a22" stroke-width=".8"/>'
    )
    return multi(items, ENMA_TF, extra)


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


def gear3(parts, order, k, extra=""):
    """Luffy's Gear 3 giant hand on a skinny arm, inflated by k about the palm; each part outlined on its own."""
    tf = (32 * (1 - k), 30 * (1 - k), 0, k)
    drawn = "".join(cel([(parts[i], (SKIN_LIT, SKIN_SH))], tf) for i in order)
    return multi([(GEAR3_ARM, "url(#skin)")]) + drawn + f'<g transform="{tfs(tf)}">{extra}</g>'


DEFS += '<linearGradient id="meat" x2="1" y2="1"><stop stop-color="#d9764a"/><stop offset="1" stop-color="#8f3b20"/></linearGradient>'


def meat():
    """Meat on the bone, upright: the text cursor."""
    knobs = [(f'<circle cx="{32 + dx}" cy="{y}" r="4.2"/>', BONE) for y in (7, 57) for dx in (-3.4, 3.4)]
    items = knobs + [
        ('<rect x="29" y="7" width="6" height="50" rx="2"/>', BONE),
        ('<path d="M32 17C43 17 46 27 45 33C44 43 38 47 32 47C26 47 20 43 19 33C18 27 21 17 32 17Z"/>', "url(#meat)"),
    ]
    return multi(items, extra='<path d="M24 26q4-5 10-6M23 35q2 4 5 5" stroke="#f4a37c" stroke-width="1.6" fill="none"/>')


# cursors --------------------------------------------------------------------------------------------------------------

POINTER, HELP, TEXT = "yoru", "badge", "meat"  # the user's picks

SPIN = range(0, 360, 15)
GLINT = [(katana(), 4000)] + [(katana(glint=g), 30) for g in range(46, 0, -6)] + [(katana(ting=t), 45) for t in (7, 9, 5)]
SHEEN = [(sticker(ARROW), 4000)] + [(sticker(ARROW, sheen=x), 30) for x in range(-12, 48, 6)]
# frames, hotspot, where badges go
CRACKLE = range(10)  # lightning seeds, one per frame
BREATH = [0.35 + 0.65 * pulse(i) for i in range(12)]  # rim brightness
POINTERS = {
    "yoru": ([(yoru(), 2400)] + [(yoru(glint=g), 35) for g in range(36, -6, -6)], (5, 4), (16, 47)),
    "clean": ([(clean(ARROW, rim=r), 130) for r in BREATH], (7, 4), (47, 47)),
    "haki": ([(haki(ARROW, ARROW_SPARKS, i), 90) for i in CRACKLE], (7, 4), (47, 47)),
    "arrow": (SHEEN, (7, 4), (47, 47)),
    "katana": (GLINT, KATANA_TIP, (16, 47)),
    "fruit": (still(gomu_fruit()), (6, 5), (16, 47)),
    "chibi": (still(chibi_point()), (6, 5), (16, 47)),
}
PTR_FRAMES, PTR_HOT, BADGE_AT = POINTERS[POINTER]
PTR = PTR_FRAMES[0][0]
PTR_ZOOM = 1.5  # Linux: the pointer family (and text) bigger than the rest; the link hand is 2x
SHAKE = [(forbidden(0), 1500)] + [(forbidden(d, f), 45) for d, f in ((-12, .5), (12, .8), (-10, .9), (10, .8), (-6, .6), (6, .4), (0, .2))]
SMOKE = [(cigarette(p), 110) for p in range(0, 360, 30)]
WONDER = [(chopper(), 1400)] + [(chopper(t, b), 70) for t, b in ((-6, -1), (-12, -2), (-12, -2), (-6, -1), (0, 0), (6, 1), (10, 1), (6, 1))]
FLOAT = [0, -0.8, -1.6, -2, -1.6, -0.8]
SWING = [(log_pose(n), 70) for n in (-35, 20, -14, 8, -4, 0)] + [(log_pose(0), HOLD)]


def badge(glyph, body=None):
    x, y = BADGE_AT
    return (body or PTR) + (
        f'<g transform="translate({x} {y})"><circle r="10.5" fill="{NAVY}"/>'
        f'<path d="{glyph}" fill="none" stroke="{WHITE}" stroke-width="3"/></g>'
    )


def menu_card():
    x, y = BADGE_AT
    return PTR + (
        f'<g transform="translate({x - 10} {y - 13})"><rect width="21" height="27" rx="1.5" fill="#f3e2b3" stroke-width="2.2"/>'
        '<path d="M3 4.5H18" stroke="#5a3a1a" stroke-width="2"/><rect x="4" y="7.5" width="13" height="10" fill="#d9c08a" stroke-width="1.2"/>'
        '<path d="M3 21H18M5 24H16" stroke="#5a3a1a" stroke-width="1.4"/></g>'
    )


HELPS = {
    "badge": still(badge(QMARK)),
    "poneglyph": [(poneglyph(0.25 + 0.25 * math.sin(math.radians(a))), 110) for a in range(0, 360, 30)],
    "chopper": WONDER,
}
TEXTS = {
    "meat": still(meat()),
    "enma": [(enma(), 2400)] + [(enma(g), 35) for g in range(56, -6, -6)],
    "steel": still(clean(IBEAM, edge=STEEL)),
    "clean": [(clean(IBEAM, rim=r), 130) for r in BREATH],
    "haki": [(haki(IBEAM, IBEAM_SPARKS, i), 120) for i in CRACKLE],
    "cigarette": SMOKE,
    "ibeam": still(sticker(IBEAM, band=False)),
}


def resize(deg):
    return still(rot(clean(DOUBLE, edge=STEEL), deg))


CURSORS = [
    Cursor("left_ptr", PTR_FRAMES, PTR_HOT, "default arrow top_left_arrow wayland-cursor pointer-move", "pointer", zoom=PTR_ZOOM),
    Cursor("right_ptr", still(f'<g transform="matrix(-1 0 0 1 64 0)">{PTR}</g>'), (64 - PTR_HOT[0], PTR_HOT[1]),
           "draft_large draft_small", zoom=PTR_ZOOM),
    Cursor("question_arrow", HELPS[HELP], PTR_HOT if HELP == "badge" else (32, 34),
           "help left_ptr_help whats_this dnd-ask 5c6cd98b3f3ebcb1f9c7f1c204630408 d9ce0ab605698f320427677b458ad60b",
           "help", zoom=PTR_ZOOM),
    Cursor("left_ptr_watch", [(yoru_working(i), 90) for i in range(12)], PTR_HOT,
           "progress 00000000000000020006000e7e9ffc3f 08e8e1c95fe2fc01f976f1e063a24ccd 3ecb610c1bf2410f44200f48c40d3599",
           "working", zoom=PTR_ZOOM),
    Cursor("wait", [(aura_ring(48, 50, 30, i % 12) + orbit(a, 48, 50, 17, 0.8), 45) for i, a in enumerate(SPIN)], (48, 48),
           "watch", "busy", grid=96, win_view=96),
    Cursor("crosshair", still(scope()), (32, 32),
           "cross cross_reverse diamond_cross tcross color-picker dotbox dot_box_mask draped_box icon target",
           "precision"),
    Cursor("xterm", TEXTS[TEXT], (32, 32), "ibeam text", "text", zoom=PTR_ZOOM),
    Cursor("vertical-text", [(rot(b, 90), ms) for b, ms in TEXTS[TEXT]], (32, 32), zoom=PTR_ZOOM),
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
           "pointer pointing_hand hand 9d800788f1b08800ae810202380a0822 e29285e634086352946a0e7090d73106", "link",
           zoom=2),
    Cursor("hand1", [(gear3(GEAR3_OPEN, (1, 2, 3, 4, 0, 5), 1 + .03 * pulse(i),
                            '<path d="M24 44Q33 49 44 42" stroke="#c98a5c" stroke-width="1.3" fill="none"/>'), 120) for i in range(12)],
           (32, 32), "grab openhand", zoom=1.5),
    Cursor("grabbing", [(gear3(GEAR3_FIST, (0, 4, 3, 2, 1, 5), 1 - .04 * pulse(i)), 120) for i in range(12)], (32, 32),
           "closedhand dnd-move dnd-none fcf21c00b30f7e3f83fe0dfd12e71cff", zoom=1.5),
    Cursor("copy", still(badge("M0-5.5V5.5M-5.5 0H5.5")), PTR_HOT,
           "dnd-copy 1081e37283d90000800003c07f3ef6bf 6407b0e94181790501fd1e167b474872 "
           "b66166c04f8c3109214a4fbd64a50fc8", zoom=PTR_ZOOM),
    Cursor("link", still(badge("M-4.5 4.5L4.5-4.5M-2-4.5H4.5V2")), PTR_HOT,
           "alias dnd-link 3085a0e285430894940527032f8b26df 640fb0e74195791501fd1ed57b41487f "
           "a2a266d0498c3104214a47bd64ab0fc8", zoom=PTR_ZOOM),
    Cursor("context-menu", still(menu_card()), PTR_HOT, zoom=PTR_ZOOM),
    Cursor("X_cursor", still(crossed()), (32, 32), "pirate x-cursor"),
    Cursor("zoom-in", still(porthole("+")), (26, 26)),
    Cursor("zoom-out", still(porthole("-")), (26, 26)),
    Cursor("plus", still(bone(10, 32, 54, 32) + bone(32, 10, 32, 54)), (32, 32), "cell"),
    Cursor("pin", SWING, (32, 30), None, "pin"),
    Cursor("person", still(hat(32, 40, 1.2)), (32, 32), None, "person"),
]

# Windows registry role -> file stem, in Control Panel scheme order
ROLES = [
    ("Arrow", "pointer"), ("Help", "help"), ("AppStarting", "working"), ("Wait", "busy"),
    ("Crosshair", "precision"), ("IBeam", "text"), ("NWPen", "handwriting"), ("No", "unavailable"),
    ("SizeNS", "vert"), ("SizeWE", "horz"), ("SizeNWSE", "dgn1"), ("SizeNESW", "dgn2"),
    ("SizeAll", "move"), ("UpArrow", "alternate"), ("Hand", "link"), ("Pin", "pin"), ("Person", "person"),
]


# rendering ------------------------------------------------------------------------------------------------------------


def render(body, px, view=GRID, zoom=1):
    png = subprocess.run(
        ["rsvg-convert", "-w", str(px), "-h", str(px)], input=svg(body, view, zoom).encode(), capture_output=True, check=True
    ).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def hotspot(hot, px, view):
    return tuple(min(px - 1, round(v * px / view)) for v in hot)


# XCursor --------------------------------------------------------------------------------------------------------------


def write_x(c, tmp):
    lines = []
    for i, (body, ms) in enumerate(c.frames):
        for size in X_SIZES:
            px = round(size * c.grid * c.zoom / GRID)
            png = tmp / f"{c.name}-{i}-{size}.png"
            render(body, px, c.grid, c.zoom).save(png)
            delay = f" {ms}" if len(c.frames) > 1 else ""
            lines.append(f"{size} {' '.join(map(str, hotspot(c.hot, px, c.grid)))} {png}{delay}")
    conf = tmp / f"{c.name}.conf"
    conf.write_text("\n".join(lines) + "\n")
    out = X_DIR / "cursors"
    subprocess.run(["xcursorgen", str(conf), str(out / c.name)], check=True)
    for alias in c.aliases.split():
        (out / alias).symlink_to(c.name)


# Windows --------------------------------------------------------------------------------------------------------------


def dib(img):
    size = img.width
    flip = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    pixels = flip.tobytes("raw", "BGRA")
    bits = flip.getchannel("A").point(lambda a: 255 if a == 0 else 0).convert("1", dither=Image.Dither.NONE).tobytes()
    src, dst = (size + 7) // 8, (size + 31) // 32 * 4
    mask = b"".join(bits[r * src : (r + 1) * src].ljust(dst, b"\0") for r in range(size))
    header = struct.pack("<IiiHHIIiiII", 40, size, 2 * size, 1, 32, 0, len(pixels) + len(mask), 0, 0, 0, 0)
    return header + pixels + mask


def cur(body, hot, view):
    entries, blobs = b"", b""
    offset = 6 + 16 * len(WIN_SIZES)
    for size in WIN_SIZES:
        blob = dib(render(body, size, view))
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, *hotspot(hot, size, view), len(blob), offset)
        blobs += blob
        offset += len(blob)
    return struct.pack("<HHH", 0, 2, len(WIN_SIZES)) + entries + blobs


def chunk(tag, data):
    return tag + struct.pack("<I", len(data)) + data + b"\0" * (len(data) % 2)


def ani(frames, hot, view):
    n = len(frames)
    rates = [max(1, round(ms * 60 / 1000)) for _, ms in frames]
    anih = struct.pack("<9I", 36, n, n, 0, 0, 0, 0, rates[0], 1)
    icons = b"".join(chunk(b"icon", cur(body, hot, view)) for body, _ in frames)
    body = b"ACON" + chunk(b"anih", anih) + chunk(b"rate", struct.pack(f"<{n}I", *rates)) + chunk(b"LIST", b"fram" + icons)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def write_win(c):
    frames = c.win_frames or c.frames
    if len(frames) > 1:
        name, data = f"{c.win}.ani", ani(frames, c.hot, c.win_view)
    else:
        name, data = f"{c.win}.cur", cur(frames[0][0], c.hot, c.win_view)
    (WIN_DIR / name).write_bytes(data)
    return name


def write_inf(files):
    path = lambda role: rf"%10%\%CUR_DIR%\{files[role]}"
    lines = [
        "[Version]", 'signature="$CHICAGO$"', "",
        "[DefaultInstall]", "CopyFiles = Scheme.Cur", "AddReg    = Scheme.Reg, Wreg", "",
        "[DestinationDirs]", 'Scheme.Cur = 10,"%CUR_DIR%"', "",
        "[Scheme.Reg]",
        rf'HKCU,"Control Panel\Cursors\Schemes","%SCHEME_NAME%",0x00020000,"{",".join(path(r) for r, _ in ROLES)}"',
        "",
        "[Wreg]", r'HKCU,"Control Panel\Cursors",,0x00020000,"%SCHEME_NAME%"',
        *(rf'HKCU,"Control Panel\Cursors",{r},0x00020000,"{path(r)}"' for r, _ in ROLES),
        r'HKLM,"SOFTWARE\Microsoft\Windows\CurrentVersion\Runonce\Setup\","",,'
        '"rundll32.exe shell32.dll,Control_RunDLL main.cpl @0"',
        "",
        "[Scheme.Cur]", *(files[r] for r, _ in ROLES), "",
        "[Strings]", r'CUR_DIR     = "Cursors\Luffy"', 'SCHEME_NAME = "Luffy"', "",
    ]
    (WIN_DIR / "install.inf").write_bytes("\r\n".join(lines).encode())


# main -----------------------------------------------------------------------------------------------------------------


def showcase(c):
    """Frame to show in the preview sheet: the longest one (rest pose)."""
    return max(c.frames, key=lambda f: f[1])[0]


def preview():
    cell = 72
    sheet = Image.new("RGBA", (cell * 8, cell * ((len(CURSORS) + 7) // 8)), "#9aa0ac")
    for i, c in enumerate(CURSORS):
        sheet.alpha_composite(render(showcase(c), 64, c.grid), (i % 8 * cell + 4, i // 8 * cell + 4))
    sheet.save(Path(__file__).with_name("preview.png"))


def main():
    for d in (X_DIR, WIN_DIR):
        shutil.rmtree(d, ignore_errors=True)
    (X_DIR / "cursors").mkdir(parents=True)
    WIN_DIR.mkdir()
    theme = "[Icon Theme]\nName=Luffy\nComment=Straw Hat Luffy cursors\n"
    (X_DIR / "index.theme").write_text(theme)
    (X_DIR / "cursor.theme").write_text(theme)

    roles = {}
    with tempfile.TemporaryDirectory() as tmp:
        for c in CURSORS:
            if c.aliases is not None:
                write_x(c, Path(tmp))
            if c.win:
                roles[c.win] = write_win(c)
    write_inf({role: roles[stem] for role, stem in ROLES})
    preview()


if __name__ == "__main__":
    main()
