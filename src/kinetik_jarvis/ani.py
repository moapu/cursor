"""Read ANI/embedded CUR images and verify lossless recoloring."""

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    offset: int
    width: int
    height: int
    xhot: int
    yhot: int

    @property
    def end(self):
        return self.offset + self.width * self.height * 4


def chunks(data, start=12, end=None):
    end = len(data) if end is None else end
    while start < end:
        if start + 8 > end:
            raise ValueError("Truncated RIFF chunk")
        tag, size = struct.unpack_from("<4sI", data, start)
        body = start + 8
        next_chunk = body + size + (size & 1)
        if next_chunk > end:
            raise ValueError("RIFF chunk exceeds its container")
        if tag == b"LIST":
            if size < 4:
                raise ValueError("Missing LIST type")
            yield from chunks(data, body + 4, body + size)
        else:
            yield tag, body, size
        start = next_chunk


def cursor_frames(data, body, length):
    if length < 6:
        raise ValueError("Truncated embedded cursor directory")
    reserved, kind, count = struct.unpack_from("<3H", data, body)
    directory_size = 6 + count * 16
    if reserved or kind != 2 or not count or directory_size > length:
        raise ValueError("Invalid embedded cursor directory")
    for i in range(count):
        width, height, _, _, hx, hy, size, offset = struct.unpack_from("<4B2H2I", data, body + 6 + i * 16)
        width, height = width or 256, height or 256
        pos = body + offset
        if offset < directory_size or offset + size > length or size < 40:
            raise ValueError("Invalid cursor image bounds")
        header, w, h, planes, depth, compression = struct.unpack_from("<IiiHHI", data, pos)
        if (header, w, h, planes, depth, compression) != (40, width, height * 2, 1, 32, 0):
            raise ValueError("Expected an uncompressed 32-bit cursor DIB")
        expected = 40 + width * height * 4 + ((width + 31) // 32 * 4) * height
        if size != expected or hx >= width or hy >= height:
            raise ValueError("Invalid cursor size or hotspot")
        yield Frame(pos + 40, width, height, hx, hy)


def frames(data, allow_legacy=False):
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"ACON":
        raise ValueError("Expected a Windows animated cursor")
    declared = struct.unpack_from("<I", data, 4)[0]
    # The supplied Aqua files incorrectly include the eight-byte RIFF header.
    if declared != len(data) - 8 and not (allow_legacy and declared == len(data)):
        raise ValueError("Incorrect RIFF length")
    result = [frame for tag, body, size in chunks(data) if tag == b"icon"
              for frame in cursor_frames(data, body, size)]
    if not result:
        raise ValueError("Animation contains no frames")
    return result


def verify(original, recolored):
    """Only visible RGB and the corrected RIFF length may change."""
    if len(original) != len(recolored):
        raise ValueError("Recoloring changed file length")
    frames(recolored)
    restored = bytearray(recolored)
    restored[4:8] = original[4:8]
    changed = False
    for frame in frames(original, allow_legacy=True):
        for pos in range(frame.offset, frame.end, 4):
            if original[pos + 3] == 0:
                continue
            changed |= original[pos:pos + 3] != recolored[pos:pos + 3]
            restored[pos:pos + 3] = original[pos:pos + 3]
    if restored != original:
        raise ValueError("Recoloring changed cursor structure or transparency")
    if not changed:
        raise ValueError("No visible colors changed")


def numbers(metadata, tag, count):
    body = metadata.get(tag)
    if body is None or len(body) != count * 4:
        raise ValueError(f"Missing or invalid ANI {tag.decode().strip()} chunk")
    return struct.unpack(f"<{count}I", body)


def animation(data):
    """Follow ANI playback order; convert 1/60-second jiffies to milliseconds."""
    images = frames(data)
    metadata = {tag: data[pos:pos + size] for tag, pos, size in chunks(data) if tag != b"icon"}
    _, count, steps, _, _, _, _, rate, flags = numbers(metadata, b"anih", 9)
    if count != len(images) or not steps:
        raise ValueError("Expected one image per ANI frame and at least one step")
    order = numbers(metadata, b"seq ", steps) if flags & 2 else tuple(range(steps))
    rates = numbers(metadata, b"rate", steps) if b"rate" in metadata else (rate,) * steps
    if any(index >= count for index in order) or any(delay == 0 for delay in rates):
        raise ValueError("Invalid ANI playback sequence or rate")
    return [(images[index], max(1, (delay * 1000 + 30) // 60)) for index, delay in zip(order, rates)]


def premultiplied(data, frame):
    """Top-down premultiplied BGRA: little-endian XCursor ARGB pixels."""
    pixels = bytearray()
    stride = frame.width * 4
    for y in range(frame.height - 1, -1, -1):
        row = frame.offset + y * stride
        for pos in range(row, row + stride, 4):
            b, g, r, a = data[pos:pos + 4]
            pixels.extend(((b * a + 127) // 255, (g * a + 127) // 255, (r * a + 127) // 255, a))
    return bytes(pixels)
