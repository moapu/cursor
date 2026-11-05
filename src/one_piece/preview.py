"""Contact sheet of each One Piece cursor's longest (rest) frame."""

from .formats import render


def preview(drawings, path):
    from PIL import Image

    cell = 72
    sheet = Image.new("RGBA", (cell * 8, cell * ((len(drawings) + 7) // 8)), "#9aa0ac")
    for i, drawing in enumerate(drawings):
        rest = max(drawing.frames, key=lambda frame: frame[1])[0]
        sheet.alpha_composite(render(rest, 64, drawing.grid), (i % 8 * cell + 4, i // 8 * cell + 4))
    sheet.save(path)
