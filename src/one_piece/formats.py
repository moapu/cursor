"""SVG rendering and XCursor / CUR / ANI encoding for One Piece artwork."""

import io
import struct
import subprocess
from functools import cache

from .svg import svg


@cache
def render(body, px, view=64, zoom=1):
    """Body rendered to a px-square RGBA image. Cached: Linux, Windows and the preview share many renders."""
    from PIL import Image

    png = subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px)], input=svg(body, view, zoom).encode(),
                         capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def hotspot(hot, px, view):
    return tuple(min(px - 1, round(v * px / view)) for v in hot)


# XCursor --------------------------------------------------------------------------------------------------------------


def xcursor(c, sizes, tmp, out):
    """Encode all SVG frames and sizes with xcursorgen; packaging owns the aliases."""
    name = c.cursor.name
    multi = len(c.frames) > 1
    lines = []
    for i, (body, ms) in enumerate(c.frames):
        for size in sizes:
            px = round(size * c.grid * c.zoom / 64)
            png = tmp / f"{name}-{i}-{size}.png"
            render(body, px, c.grid, c.zoom).save(png)
            lines.append(f"{size} {' '.join(map(str, hotspot(c.hot, px, c.grid)))} {png}" + (f" {ms}" if multi else ""))
    conf = tmp / f"{name}.conf"
    conf.write_text("\n".join(lines) + "\n")
    subprocess.run(["xcursorgen", str(conf), str(out / name)], check=True)


# Windows --------------------------------------------------------------------------------------------------------------


def dib(img):
    """32-bit BMP (DIB) with an AND mask, as stored inside .cur files."""
    from PIL import Image

    size = img.width
    flip = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    pixels = flip.tobytes("raw", "BGRA")
    bits = flip.getchannel("A").point(lambda a: 255 if a == 0 else 0).convert("1", dither=Image.Dither.NONE).tobytes()
    src, dst = (size + 7) // 8, (size + 31) // 32 * 4
    mask = b"".join(bits[r * src : (r + 1) * src].ljust(dst, b"\0") for r in range(size))
    header = struct.pack("<IiiHHIIiiII", 40, size, 2 * size, 1, 32, 0, len(pixels) + len(mask), 0, 0, 0, 0)
    return header + pixels + mask


def cur(body, hot, view, sizes):
    entries, blobs = b"", b""
    offset = 6 + 16 * len(sizes)
    for size in sizes:
        blob = dib(render(body, size, view))
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, *hotspot(hot, size, view), len(blob), offset)
        blobs += blob
        offset += len(blob)
    return struct.pack("<HHH", 0, 2, len(sizes)) + entries + blobs


def chunk(tag, data):
    return tag + struct.pack("<I", len(data)) + data + b"\0" * (len(data) % 2)


def ani(frames, hot, view, sizes):
    n = len(frames)
    rates = [max(1, round(ms * 60 / 1000)) for _, ms in frames]  # jiffies
    anih = struct.pack("<9I", 36, n, n, 0, 0, 0, 0, rates[0], 1)
    icons = b"".join(chunk(b"icon", cur(body, hot, view, sizes)) for body, _ in frames)
    body = b"ACON" + chunk(b"anih", anih) + chunk(b"rate", struct.pack(f"<{n}I", *rates)) + chunk(b"LIST", b"fram" + icons)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def windows(c, sizes):
    """Encode a drawing as CUR or ANI bytes; shared packaging writes the file."""
    if len(c.frames) == 1:
        return cur(c.frames[0][0], c.hot, c.grid, sizes)
    return ani(c.frames, c.hot, c.grid, sizes)
