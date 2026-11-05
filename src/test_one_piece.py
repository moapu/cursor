"""One Piece catalog and encoder contracts; rendering tools are not required."""

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from build import main
from kinetik_jarvis.ani import chunks, frames
from one_piece import formats
from one_piece.theme import CURSORS, DRAWINGS, THEME, WIN_SIZES, X_SIZES, build

SCRATCH = Path("/tmp/ai")


class OnePieceTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)

    def test_catalog_and_svg_frames_unchanged_by_refactor(self):
        # Snapshot from the original builder: art, timing, hotspots, sizes and platform roles.
        manifest = [(d.cursor.name, d.cursor.aliases, d.cursor.role, d.cursor.file, d.cursor.linux,
                     d.frames, d.hot, d.grid, d.zoom) for d in DRAWINGS]
        digest = hashlib.sha256(json.dumps(manifest).encode()).hexdigest()
        self.assertEqual(digest, "8ad8b84a5c9283c369b7e56db81ef0dc49f00111f90f95b040e7919aca9fbdc3")
        self.assertEqual(len(CURSORS), 31)

    def test_catalog_matches_windows_encoder_choice(self):
        for drawing in DRAWINGS:
            cursor = drawing.cursor
            if not cursor.file:
                continue
            expected = ".ani" if len(drawing.frames) > 1 else ".cur"
            self.assertEqual(Path(cursor.file).suffix, expected)
        self.assertEqual([cursor.name for cursor in CURSORS if not cursor.linux], ["pin", "person"])

    def test_windows_dispatches_static_and_animated_drawings(self):
        with patch.object(formats, "cur", return_value=b"cur") as cur, \
                patch.object(formats, "ani", return_value=b"ani") as ani:
            for drawing in DRAWINGS:
                data = formats.windows(drawing, WIN_SIZES)
                if len(drawing.frames) == 1:
                    self.assertEqual(data, b"cur")
                    cur.assert_called_with(drawing.frames[0][0], drawing.hot, drawing.grid, WIN_SIZES)
                else:
                    self.assertEqual(data, b"ani")
                    ani.assert_called_with(drawing.frames, drawing.hot, drawing.grid, WIN_SIZES)

    def test_cur_directory_sizes_hotspots_and_offsets(self):
        sizes = (24, 32, 96)
        with patch.object(formats, "render", side_effect=lambda body, size, view: size), \
                patch.object(formats, "dib", side_effect=lambda size: bytes(size)):
            data = formats.cur("art", (5, 4), 64, sizes)
        self.assertEqual(struct.unpack_from("<3H", data), (0, 2, len(sizes)))
        offset = 6 + 16 * len(sizes)
        for i, size in enumerate(sizes):
            entry = struct.unpack_from("<4B2H2I", data, 6 + i * 16)
            self.assertEqual(entry, (size, size, 0, 0, round(5 * size / 64), round(4 * size / 64), size, offset))
            self.assertEqual(data[offset:offset + size], bytes(size))
            offset += size
        self.assertEqual(offset, len(data))

    def test_ani_preserves_frames_multisize_icons_and_rates(self):
        def dib(size):
            pixels = bytes((20, 40, 60, 255)) * size * size
            mask = bytes(((size + 31) // 32 * 4) * size)
            return struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                               len(pixels + mask), 0, 0, 0, 0) + pixels + mask

        with patch.object(formats, "render", side_effect=lambda body, size, view: size), \
                patch.object(formats, "dib", side_effect=dib):
            data = formats.ani([("a", 0), ("b", 45), ("c", 3_600_000)], (32, 32), 64, (2, 4))
        self.assertEqual(struct.unpack_from("<I", data, 4)[0], len(data) - 8)
        metadata = {tag: data[pos:pos + size] for tag, pos, size in chunks(data) if tag != b"icon"}
        self.assertEqual(struct.unpack("<9I", metadata[b"anih"]), (36, 3, 3, 0, 0, 0, 0, 1, 1))
        self.assertEqual(struct.unpack("<3I", metadata[b"rate"]), (1, 3, 216_000))
        self.assertEqual([(f.width, f.height, f.xhot, f.yhot) for f in frames(data)],
                         [(2, 2, 1, 1), (4, 4, 2, 2)] * 3)

    def test_xcursor_retains_size_zoom_hotspots_and_delays(self):
        for drawing in (DRAWINGS[0], DRAWINGS[4], DRAWINGS[19]):
            with self.subTest(cursor=drawing.cursor.name), \
                    patch.object(formats, "render", return_value=Mock()) as render, \
                    patch.object(formats.subprocess, "run") as run:
                formats.xcursor(drawing, X_SIZES, self.output, self.output)
                config = self.output / f"{drawing.cursor.name}.conf"
                lines = config.read_text().splitlines()
                self.assertEqual(len(lines), len(drawing.frames) * len(X_SIZES))
                for i, ((body, delay), size) in enumerate((frame, size) for frame in drawing.frames for size in X_SIZES):
                    px = round(size * drawing.grid * drawing.zoom / 64)
                    render.assert_any_call(body, px, drawing.grid, drawing.zoom)
                    hot = formats.hotspot(drawing.hot, px, drawing.grid)
                    png = self.output / f"{drawing.cursor.name}-{i // len(X_SIZES)}-{size}.png"
                    expected = f"{size} {hot[0]} {hot[1]} {png}"
                    if len(drawing.frames) > 1:
                        expected += f" {delay}"
                    self.assertEqual(lines[i], expected)
                run.assert_called_once_with(["xcursorgen", str(config), str(self.output / drawing.cursor.name)], check=True)

    def test_cli_uses_one_output_directory(self):
        default = Path(__file__).resolve().parents[1] / "OnePiece"
        for argv, expected in ((["build.py"], default), (["build.py", "--output", str(self.output)], self.output)):
            with self.subTest(argv=argv), patch("sys.argv", argv), patch("build.build") as export:
                main()
                export.assert_called_once_with(expected)

    def test_build_uses_shared_packaging_and_preserves_unrelated_files(self):
        output = self.output / "OnePiece"
        output.mkdir()
        keep = output / "README.md"
        keep.write_bytes(b"keep")
        preview = output / "preview.png"

        def encode_linux(drawing, sizes, tmp, directory):
            (directory / drawing.cursor.name).write_bytes(b"XCursor")

        with patch("one_piece.theme.xcursor", side_effect=encode_linux), \
                patch("one_piece.theme.encode_windows", return_value=b"Windows"), \
                patch("one_piece.theme.preview") as paint:
            build(output)
            build(output)
            paint.assert_called_with(DRAWINGS, preview)
        self.assertEqual(keep.read_bytes(), b"keep")
        self.assertEqual((output / "cursors/default").readlink(), Path("left_ptr"))
        self.assertFalse((output / "cursors/pin").exists())
        self.assertTrue((output / "index.theme").is_file())
        for cursor in THEME.windows:
            self.assertEqual((output / cursor.file).read_bytes(), b"Windows")


if __name__ == "__main__":
    unittest.main()
