"""Recolor Kinetik Aqua for Windows and Linux/NixOS using only Python's standard library."""

import argparse
from pathlib import Path

from kinetik_jarvis.theme import FOLDER, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original kinetik-aqua-x directory")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / FOLDER)
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == "__main__":
    main()
