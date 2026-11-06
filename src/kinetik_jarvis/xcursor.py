"""Resample premultiplied pixels and encode native Linux XCursor animations."""

import math
import struct
from functools import cache

from .ani import animation, premultiplied

SIZES = (24, 32, 48, 64, 96)
ZOOM = 1.5  # drawn bigger than the nominal size, like OnePiece's pointer
IMAGE_TYPE = 0xFFFD0002


@cache
def weights(source, target):
    """Area averaging when shrinking; bilinear interpolation when enlarging."""
    if source < 1 or target < 1:
        raise ValueError("Image dimensions must be positive")
    ratio = source / target
    result = []
    for dest in range(target):
        if target < source:
            start, end = dest * ratio, (dest + 1) * ratio
            result.append(tuple((index, (min(end, index + 1) - max(start, index)) / ratio)
                                for index in range(math.floor(start), math.ceil(end))))
            continue
        center = (dest + 0.5) * ratio - 0.5
        low = math.floor(center)
        fraction = center - low
        result.append(((max(0, min(source - 1, low)), 1 - fraction),
                       (max(0, min(source - 1, low + 1)), fraction)))
    return tuple(result)


def blend(vectors, samples):
    """Weighted sums of whole vectors; sum() keeps a per-pixel loop's float result."""
    return [list(map(sum, zip(*([value * weight for value in vectors[index]] for index, weight in taps))))
            for taps in samples]


def resize(pixels, width, height, size):
    """Separable resampling, one channel plane at a time (columns, then rows)."""
    if (width, height) == (size, size):
        return pixels
    xweights, yweights = weights(width, size), weights(height, size)
    stride, output = width * 4, bytearray(size * size * 4)
    for channel in range(4):
        columns = list(zip(*(pixels[y * stride + channel:(y + 1) * stride:4] for y in range(height))))
        rows = list(zip(*blend(columns, xweights)))
        output[channel::4] = bytes(round(value) for row in blend(rows, yweights) for value in row)
    return bytes(output)


def xcursor(data, sizes=SIZES, zoom=ZOOM):
    """XCursor 1.0 format, checked against libXcursor 1.2.3's Xcursor.h."""
    sequence = animation(data)
    table, body = bytearray(), bytearray()
    entries = len(sequence) * len(sizes)
    position = 16 + entries * 12
    pixels = {frame: premultiplied(data, frame) for frame in dict(sequence)}
    for size in sizes:
        px = round(size * zoom)
        scaled = {frame: resize(image, frame.width, frame.height, px) for frame, image in pixels.items()}
        for frame, delay in sequence:
            xhot = min(px - 1, round(frame.xhot * px / frame.width))
            yhot = min(px - 1, round(frame.yhot * px / frame.height))
            image = struct.pack("<9I", 36, IMAGE_TYPE, size, 1, px, px, xhot, yhot, delay)
            image += scaled[frame]
            table.extend(struct.pack("<3I", IMAGE_TYPE, size, position))
            body.extend(image)
            position += len(image)
    return struct.pack("<4I", 0x72756358, 16, 0x10000, entries) + table + body
