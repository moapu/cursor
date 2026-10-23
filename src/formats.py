"""Rendering and the two output formats: XCursor (Linux) and .cur/.ani + install.inf (Windows)."""

import io
import struct
import subprocess
from functools import cache

from PIL import Image

from svg import svg


@cache
def render(body, px, view=64, zoom=1):
    """Body rendered to a px-square RGBA image. Cached: Linux, Windows and the preview share many renders."""
    png = subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px)], input=svg(body, view, zoom).encode(),
                         capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def hotspot(hot, px, view):
    return tuple(min(px - 1, round(v * px / view)) for v in hot)


# XCursor --------------------------------------------------------------------------------------------------------------


def xcursor(c, sizes, tmp, out):
    """Write cursor `c` (all frames, all sizes) to out/<name> with xcursorgen, plus its alias symlinks."""
    multi = len(c.frames) > 1
    lines = []
    for i, (body, ms) in enumerate(c.frames):
        for size in sizes:
            px = round(size * c.grid * c.zoom / 64)
            png = tmp / f"{c.name}-{i}-{size}.png"
            render(body, px, c.grid, c.zoom).save(png)
            lines.append(f"{size} {' '.join(map(str, hotspot(c.hot, px, c.grid)))} {png}" + (f" {ms}" if multi else ""))
    conf = tmp / f"{c.name}.conf"
    conf.write_text("\n".join(lines) + "\n")
    subprocess.run(["xcursorgen", str(conf), str(out / c.name)], check=True)
    for alias in c.aliases.split():
        (out / alias).symlink_to(c.name)


# Windows --------------------------------------------------------------------------------------------------------------


def dib(img):
    """32-bit BMP (DIB) with an AND mask, as stored inside .cur files."""
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


def windows(c, sizes, out):
    """Write cursor `c` as <win>.cur or <win>.ani; returns the file name."""
    if len(c.frames) == 1:
        name, data = f"{c.win}.cur", cur(c.frames[0][0], c.hot, c.win_view, sizes)
    else:
        name, data = f"{c.win}.ani", ani(c.frames, c.hot, c.win_view, sizes)
    (out / name).write_bytes(data)
    return name


def inf(roles, files, out, folder, title):
    """install.inf: copies the files to %WINDIR%\\Cursors\\<folder> and registers them as the `title` scheme."""
    path = lambda role: rf"%10%\%CUR_DIR%\{files[role]}"
    lines = [
        "[Version]", 'signature="$CHICAGO$"', "",
        "[DefaultInstall]", "CopyFiles = Scheme.Cur", "AddReg    = Scheme.Reg, Wreg", "",
        "[DestinationDirs]", 'Scheme.Cur = 10,"%CUR_DIR%"', "",
        "[Scheme.Reg]",
        rf'HKCU,"Control Panel\Cursors\Schemes","%SCHEME_NAME%",0x00020000,"{",".join(path(r) for r in roles)}"',
        "",
        "[Wreg]", r'HKCU,"Control Panel\Cursors",,0x00020000,"%SCHEME_NAME%"',
        *(rf'HKCU,"Control Panel\Cursors",{r},0x00020000,"{path(r)}"' for r in roles),
        r'HKLM,"SOFTWARE\Microsoft\Windows\CurrentVersion\Runonce\Setup\","",,'
        '"rundll32.exe shell32.dll,Control_RunDLL main.cpl @0"',
        "",
        "[Scheme.Cur]", *(files[r] for r in roles), "",
        "[Strings]", rf'CUR_DIR     = "Cursors\{folder}"', f'SCHEME_NAME = "{title}"', "",
    ]
    (out / "install.inf").write_bytes("\r\n".join(lines).encode())
