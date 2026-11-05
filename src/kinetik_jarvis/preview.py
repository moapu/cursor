"""Dependency-free PNG contact sheets for generated cursor themes."""

import struct
import zlib

from .ani import frames


def png(path, width, height, rgb):
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    scanlines = b"".join(b"\0" + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    header = struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                     chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))


def paint(rgb, width, x0, y0, data, frame, background):
    for y in range(frame.height):
        for x in range(frame.width):
            pos = frame.offset + ((frame.height - y - 1) * frame.width + x) * 4
            b, g, r, a = data[pos:pos + 4]
            color = bytes((v * a + back * (255 - a)) // 255 for v, back in zip((r, g, b), background))
            for yy in range(2):
                for xx in range(2):
                    dest = ((y0 + y * 2 + yy) * width + x0 + x * 2 + xx) * 3
                    rgb[dest:dest + 3] = color


def preview(cursors, path):
    cell, cols = 144, 5
    rows = (len(cursors) + cols - 1) // cols
    width, height = cell * cols, cell * rows * 2
    backgrounds = ((22, 30, 43), (233, 238, 244))
    rgb = bytearray(b"".join(bytes(bg) * width * cell * rows for bg in backgrounds))
    for index, data in enumerate(cursors.values()):
        images = frames(data)
        frame = images[len(images) // 2]
        for panel, background in enumerate(backgrounds):
            x0 = (index % cols) * cell + 8
            y0 = (index // cols + panel * rows) * cell + 8
            paint(rgb, width, x0, y0, data, frame, background)
    png(path, width, height, rgb)
