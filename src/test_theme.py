"""Shared packaging contracts for every cursor theme, without rendering dependencies."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from kinetik_jarvis.theme import THEME as KINETIK
from one_piece.theme import THEME as ONE_PIECE
from theme import Cursor, Theme, installer, linux, windows

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path("/tmp/ai")
THEMES = ((ONE_PIECE, ROOT / "OnePiece"), (KINETIK, ROOT / "Kinetik-JARVIS"))


def section(text, name):
    return text.split(f"[{name}]\n", 1)[1].split("\n\n", 1)[0].splitlines()


class PackagingTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)

    def test_both_themes_use_shared_catalog(self):
        for theme, _ in THEMES:
            with self.subTest(theme=theme.folder):
                self.assertIsInstance(theme, Theme)
                self.assertTrue(all(isinstance(cursor, Cursor) for cursor in theme.cursors))
                self.assertEqual(len(theme.windows), 17 if theme is ONE_PIECE else 15)

    def test_shipped_themes_use_one_folder_for_both_platforms(self):
        for theme, output in THEMES:
            with self.subTest(theme=theme.folder):
                self.assertTrue((output / "cursors").is_dir())
                for name in ("index.theme", "cursor.theme", "install.inf", "preview.png"):
                    self.assertTrue((output / name).is_file(), name)
                for cursor in theme.windows:
                    self.assertTrue((output / cursor.file).is_file(), cursor.file)
                self.assertFalse((ROOT / f"{theme.folder}-Windows").exists())

    def test_installer_preserves_existing_schemes_and_activation(self):
        for theme, shipped in THEMES:
            with self.subTest(theme=theme.folder):
                actual = installer(theme).decode("ascii").replace("\r\n", "\n")
                expected = (shipped / "install.inf").read_text()
                self.assertEqual(section(actual, "Scheme.Reg"), section(expected, "Scheme.Reg"))
                self.assertEqual([line.strip('"') for line in section(actual, "Scheme.Cur")],
                                 [line.strip('"') for line in section(expected, "Scheme.Cur")])
                self.assertEqual("[Wreg]" in actual, theme.activate)
                if theme.activate:
                    self.assertEqual(section(actual, "Wreg"), section(expected, "Wreg"))
                self.assertTrue(all('"' in line for line in section(actual, "Scheme.Cur")))
                self.assertNotIn(b"\n", installer(theme).replace(b"\r\n", b""))

    def test_linux_metadata_and_aliases_match_shipped_themes(self):
        for theme, shipped in THEMES:
            with self.subTest(theme=theme.folder):
                output = self.output / theme.folder
                directory = output / "cursors"
                directory.mkdir(parents=True)
                for cursor in theme.cursors:
                    if cursor.linux:
                        (directory / cursor.name).write_bytes(b"encoded cursor")
                linux(theme, output)
                linux(theme, output)
                expected_names = set()
                for cursor in theme.cursors:
                    if not cursor.linux:
                        self.assertFalse((directory / cursor.name).exists())
                        continue
                    expected_names.update((cursor.name, *cursor.aliases))
                    for alias in cursor.aliases:
                        self.assertEqual((directory / alias).readlink(), Path(cursor.name))
                        self.assertEqual((shipped / "cursors" / alias).readlink(), Path(cursor.name))
                self.assertEqual({path.name for path in directory.iterdir()}, expected_names)
                for name in ("index.theme", "cursor.theme"):
                    self.assertEqual((output / name).read_bytes(), (shipped / name).read_bytes())

    def test_linux_protects_regular_alias_files(self):
        directory = self.output / "cursors"
        directory.mkdir()
        (directory / "left_ptr").write_bytes(b"cursor")
        alias = directory / "default"
        alias.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            linux(ONE_PIECE, self.output)
        self.assertEqual(alias.read_bytes(), b"keep")

    def test_linux_rejects_missing_canonical_file(self):
        with self.assertRaises(FileNotFoundError):
            linux(ONE_PIECE, self.output)
        self.assertFalse((self.output / "index.theme").exists())

    def test_windows_writes_only_catalog_files_and_preserves_unrelated_files(self):
        for theme, _ in THEMES:
            with self.subTest(theme=theme.folder):
                output = self.output / theme.folder
                output.mkdir()
                keep = output / "README.md"
                keep.write_bytes(b"keep")
                encoded = {cursor.file: cursor.name.encode() for cursor in theme.windows}
                encoded["unused.ani"] = b"not in catalog"
                windows(theme, encoded, output)
                self.assertEqual(keep.read_bytes(), b"keep")
                self.assertFalse((output / "unused.ani").exists())
                for cursor in theme.windows:
                    self.assertEqual((output / cursor.file).read_bytes(), encoded[cursor.file])
                self.assertEqual((output / "install.inf").read_bytes(), installer(theme))

    def test_windows_rejects_missing_files_before_writing(self):
        with self.assertRaisesRegex(ValueError, "Missing Windows cursors"):
            windows(ONE_PIECE, {}, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_catalog_rejects_duplicate_linux_names(self):
        for cursor in (Cursor("left_ptr"), Cursor("other", ("left_ptr",)), Cursor("default")):
            with self.subTest(cursor=cursor), self.assertRaisesRegex(ValueError, "Duplicate Linux"):
                replace(ONE_PIECE, cursors=(*ONE_PIECE.cursors, cursor))

    def test_catalog_rejects_invalid_or_duplicate_windows_entries(self):
        for cursor in (Cursor("other", role="Arrow", file="other.cur"),
                       Cursor("other", role="Person", file="Normal.ani"),
                       Cursor("other", role="Unknown", file="other.cur"),
                       Cursor("other", role="Arrow"), Cursor("other", file="other.cur")):
            with self.subTest(cursor=cursor), self.assertRaises(ValueError):
                replace(KINETIK, cursors=(*KINETIK.cursors, cursor))


if __name__ == "__main__":
    unittest.main()
