"""Unit tests plus optional integration tests against the original Aqua animations."""

import os
import struct
import tempfile
import unittest
from pathlib import Path

from kinetik_jarvis.ani import animation, chunks, frames, premultiplied, verify
from kinetik_jarvis.theme import CURSORS, CYAN, THEME, linux, metal, recolor
from theme import installer
from kinetik_jarvis.xcursor import IMAGE_TYPE, SIZES, resize, weights, xcursor

SOURCE = Path(os.environ.get(
    "KINETIK_SOURCE", str(Path(__file__).resolve().parents[2] / "work-configs/cursor/kinetik-aqua-x")
))
SCRATCH = Path("/tmp/ai")


def chunk(tag, body):
    return tag + struct.pack("<I", len(body)) + body + b"\0" * (len(body) & 1)


def sample(sequence=None, rate=5, legacy=False):
    """A self-contained 2×2 cursor with opaque, translucent and transparent pixels."""
    pixels = bytes((217, 255, 0, 255, 80, 80, 80, 128, 255, 255, 255, 0, 0, 0, 0, 255))
    mask = b"\0" * 4 + b"\x80\0\0\0"
    dib = struct.pack("<IiiHHIIiiII", 40, 2, 4, 1, 32, 0, len(pixels + mask), 0, 0, 0, 0)
    image = dib + pixels + mask
    icon = struct.pack("<3H4B2H2I", 0, 2, 1, 2, 2, 0, 0, 1, 1, len(image), 22) + image
    steps = 1 if sequence is None else len(sequence)
    header = struct.pack("<9I", 36, 1, steps, 2, 2, 32, 1, rate, 1 if sequence is None else 3)
    body = b"ACON" + chunk(b"anih", header) + chunk(b"LIST", b"fram" + chunk(b"icon", icon))
    if sequence is not None:
        body += chunk(b"seq ", struct.pack(f"<{steps}I", *sequence))
    return b"RIFF" + struct.pack("<I", len(body) + (8 if legacy else 0)) + body


def metadata(data):
    return {tag: data[pos:pos + size] for tag, pos, size in chunks(data) if tag != b"icon"}


def images(data):
    count = struct.unpack_from("<I", data, 12)[0]
    for i in range(count):
        kind, size, pos = struct.unpack_from("<3I", data, 16 + i * 12)
        header = struct.unpack_from("<9I", data, pos)
        length, _, _, _, width, height, _, _, _ = header
        yield kind, size, header, data[pos + length:pos + length + width * height * 4]


class UnitTests(unittest.TestCase):
    def test_catalog_is_unique(self):
        names = [name for cursor in CURSORS for name in (cursor.name, *cursor.aliases)]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len({cursor.role for cursor in CURSORS}), 15)
        self.assertEqual(len({cursor.file for cursor in CURSORS}), 15)

    def test_arc_reactor_palette(self):
        original = sample()
        pos = frames(original)[0].offset
        output = recolor(original)
        self.assertEqual(output[pos:pos + 4], bytes((*reversed(CYAN), 255)))
        self.assertEqual(metal(0), (4, 7, 12))
        self.assertEqual(metal(255), (255, 244, 218))

    def test_legacy_length_is_corrected(self):
        original = sample(legacy=True)
        with self.assertRaisesRegex(ValueError, "RIFF length"):
            frames(original)
        self.assertEqual(frames(original, allow_legacy=True), frames(recolor(original)))

    def test_default_animation_rate(self):
        original = sample()
        self.assertEqual(animation(original), [(frames(original)[0], 83)])

    def test_repeated_animation_steps(self):
        original = sample(sequence=(0, 0), rate=6)
        self.assertEqual(animation(original), [(frames(original)[0], 100)] * 2)
        self.assertEqual(len(list(images(xcursor(original, sizes=(2,))))), 2)

    def test_invalid_animation_order_and_rate(self):
        for original in (sample(sequence=(1,)), sample(rate=0)):
            with self.subTest(cursor=original), self.assertRaisesRegex(ValueError, "sequence or rate"):
                animation(original)

    def test_missing_animation_metadata(self):
        original = sample()
        pos = next(pos for tag, pos, _ in chunks(original) if tag == b"anih")
        damaged = bytearray(original)
        damaged[pos - 8:pos - 4] = b"junk"
        with self.assertRaisesRegex(ValueError, "anih"):
            animation(damaged)

    def test_truncated_input(self):
        for original in (b"", b"RIFF", sample()[:-1]):
            with self.subTest(cursor=original), self.assertRaises(ValueError):
                frames(original)

    def test_short_icon_directory(self):
        body = b"ACON" + chunk(b"icon", b"\0\0")
        original = b"RIFF" + struct.pack("<I", len(body)) + body
        with self.assertRaisesRegex(ValueError, "cursor directory"):
            frames(original)

    def test_constant_pixels_survive_resizing(self):
        color = bytes((20, 40, 60, 100))
        for size in (1, 2, 3, 5):
            self.assertEqual(resize(color * 4, 2, 2, size), color * size * size)

    def test_sampling_weights_are_cached_and_immutable(self):
        samples = weights(64, 24)
        self.assertIs(samples, weights(64, 24))
        self.assertIsInstance(samples, tuple)
        self.assertTrue(all(isinstance(row, tuple) for row in samples))
        for source, target in ((0, 24), (64, 0)):
            with self.assertRaisesRegex(ValueError, "positive"):
                weights(source, target)

    def test_linux_aliases_and_theme_metadata(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cursors = {cursor.file: sample() for cursor in CURSORS}
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            output = Path(directory)
            linux(cursors, output)
            for cursor in CURSORS:
                self.assertTrue((output / "cursors" / cursor.name).is_file())
                for alias in cursor.aliases:
                    self.assertEqual((output / "cursors" / alias).readlink(), Path(cursor.name))
                    self.assertTrue((output / "cursors" / alias).is_file())
            for name in ("index.theme", "cursor.theme"):
                self.assertIn("Name=Kinetik JARVIS", (output / name).read_text())
            linux(cursors, output)
            self.assertTrue((output / "cursors/default").is_symlink())

    def test_linux_does_not_overwrite_alias_files(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            output = Path(directory)
            (output / "cursors").mkdir()
            alias = output / "cursors/default"
            alias.write_bytes(b"keep this")
            with self.assertRaises(FileExistsError):
                linux({cursor.file: sample() for cursor in CURSORS}, output)
            self.assertEqual(alias.read_bytes(), b"keep this")


class OriginalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [cursor.file for cursor in CURSORS if not (SOURCE / cursor.file).is_file()]
        if missing:
            message = f"Missing Aqua files in {SOURCE}; set KINETIK_SOURCE to the original theme directory"
            if "KINETIK_SOURCE" in os.environ:
                raise FileNotFoundError(message)
            raise unittest.SkipTest(message)
        cls.originals = {cursor.file: (SOURCE / cursor.file).read_bytes() for cursor in CURSORS}
        cls.cursors = {name: recolor(data) for name, data in cls.originals.items()}

    def test_all_original_animations(self):
        total = 0
        for name, original in self.originals.items():
            with self.subTest(cursor=name):
                output = self.cursors[name]
                source_frames = frames(original, allow_legacy=True)
                self.assertEqual(source_frames, frames(output))
                self.assertEqual(struct.unpack_from("<I", output, 4)[0], len(output) - 8)
                self.assertEqual(len(original), len(output))
                self.assertNotEqual(original, output)
                verify(original, output)
                total += len(source_frames)
                for frame in source_frames:
                    self.assertEqual(original[frame.offset + 3:frame.end:4], output[frame.offset + 3:frame.end:4])
                self.assertEqual(metadata(original), metadata(output))
        self.assertEqual(total, 203)

    def test_reject_changed_alpha(self):
        original = self.originals["Normal.ani"]
        output = bytearray(self.cursors["Normal.ani"])
        output[frames(original, allow_legacy=True)[0].offset + 3] ^= 1
        with self.assertRaisesRegex(ValueError, "transparency"):
            verify(original, output)

    def test_reject_changed_timing(self):
        original = self.originals["Normal.ani"]
        output = bytearray(self.cursors["Normal.ani"])
        rate_pos = next(pos for tag, pos, _ in chunks(original) if tag == b"rate")
        output[rate_pos] ^= 1
        with self.assertRaisesRegex(ValueError, "structure"):
            verify(original, output)

    def test_installer_references_existing_files(self):
        inf = installer(THEME).decode("ascii")
        self.assertIn('SCHEME_NAME = "Kinetik JARVIS"', inf)
        copied = inf.split("[Scheme.Cur]\r\n")[1].split("\r\n\r\n")[0].splitlines()
        self.assertEqual([name.strip('"') for name in copied], [cursor.file for cursor in CURSORS])
        self.assertTrue(all(name.strip('"') in self.originals for name in copied))
        self.assertNotIn("Button.ani", inf)
        self.assertNotIn("Scheme.Txt", inf)
        self.assertEqual(inf.split("[Scheme.Reg]\r\n")[1].splitlines()[0].count(",%10%"), 14)

    def test_linux_native_pixels_hotspots_and_timing(self):
        for name, source in self.cursors.items():
            with self.subTest(cursor=name):
                sequence = animation(source)
                data = xcursor(source, sizes=(64,))
                self.assertEqual(struct.unpack_from("<4I", data), (0x72756358, 16, 0x10000, len(sequence)))
                for (frame, delay), (kind, size, header, pixels) in zip(sequence, images(data)):
                    self.assertEqual((kind, size), (IMAGE_TYPE, 64))
                    self.assertEqual(header, (36, IMAGE_TYPE, 64, 1, 64, 64, frame.xhot, frame.yhot, delay))
                    self.assertEqual(pixels, premultiplied(source, frame))

    def test_linux_all_sizes_and_premultiplied_alpha(self):
        data = xcursor(self.cursors["Normal.ani"])
        count = struct.unpack_from("<I", data, 12)[0]
        self.assertEqual(count, 11 * len(SIZES))
        seen = set()
        for kind, size, header, pixels in images(data):
            length, _, _, version, w, h, hx, hy, delay = header
            self.assertEqual((kind, length, version, w, h), (IMAGE_TYPE, 36, 1, size, size))
            self.assertTrue(0 <= hx < w and 0 <= hy < h and delay > 0)
            seen.add(size)
            self.assertEqual(len(pixels), w * h * 4)
            self.assertTrue(all(max(b, g, r) <= a for b, g, r, a in zip(
                pixels[::4], pixels[1::4], pixels[2::4], pixels[3::4]
            )))
        self.assertEqual(seen, set(SIZES))

    def test_linux_uses_ani_sequence_and_rates(self):
        data = bytearray(self.cursors["Normal.ani"])
        offsets = {tag: pos for tag, pos, _ in chunks(data)}
        struct.pack_into("<I", data, offsets[b"seq "], 10)
        struct.pack_into("<I", data, offsets[b"rate"], 6)
        self.assertEqual(animation(data)[0], (frames(data)[10], 100))

    def test_reject_invalid_riff_length(self):
        original = bytearray(self.originals["Normal.ani"])
        struct.pack_into("<I", original, 4, 0)
        with self.assertRaisesRegex(ValueError, "RIFF length"):
            recolor(original)


if __name__ == "__main__":
    unittest.main()
