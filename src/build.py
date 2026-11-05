"""Build One Piece cursors for Linux and Windows."""

import argparse
from pathlib import Path

from one_piece.theme import FOLDER, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / FOLDER,
                        help="Theme directory containing Linux, Windows and preview assets")
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
