"""Resample premultiplied pixels and encode native Linux XCursor animations."""

import math
import struct
from functools import cache

from .ani import animation, premultiplied

SIZES = (24, 32, 48, 64, 96)
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


def resize(pixels, width, height, size):
    if (width, height) == (size, size):
        return pixels
    horizontal = []
    xweights, yweights = weights(width, size), weights(height, size)
    for y in range(height):
        for samples in xweights:
            horizontal.append(tuple(sum(pixels[(y * width + x) * 4 + channel] * weight
                                        for x, weight in samples) for channel in range(4)))
    output = bytearray()
    for samples in yweights:
        for x in range(size):
            output.extend(round(sum(horizontal[y * size + x][channel] * weight for y, weight in samples))
                          for channel in range(4))
    return bytes(output)


def xcursor(data, sizes=SIZES):
    """XCursor 1.0 format, checked against libXcursor 1.2.3's Xcursor.h."""
    sequence = animation(data)
    table, body = bytearray(), bytearray()
    entries = len(sequence) * len(sizes)
    position = 16 + entries * 12
    pixels = {frame: premultiplied(data, frame) for frame in dict(sequence)}
    for size in sizes:
        for frame, delay in sequence:
            xhot = min(size - 1, round(frame.xhot * size / frame.width))
            yhot = min(size - 1, round(frame.yhot * size / frame.height))
            image = struct.pack("<9I", 36, IMAGE_TYPE, size, 1, size, size, xhot, yhot, delay)
            image += resize(pixels[frame], frame.width, frame.height, size)
            table.extend(struct.pack("<3I", IMAGE_TYPE, size, position))
            body.extend(image)
            position += len(image)
    return struct.pack("<4I", 0x72756358, 16, 0x10000, entries) + table + body
