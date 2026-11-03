"""Join the capture.cjs screenshots into one side-by-side image per step and one GIF per column."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
SHOTS = HERE / "shots"
COLUMNS = [
    ("main", "main today"),
    ("pencil", "prototype: pencil"),
    ("radio", "variant C: radio"),
]
STEPS = [
    ("1-edit-mode", "1. Open sample, click Edit"),
    ("2-draw-before-pick", "2. Draw a box before picking a source"),
    ("3-picked-model_v2", "3. Pick model_v2"),
    ("4-deer-box-in-model_v2", "4. Draw the deer box"),
]
TILE_WIDTH = 960
LABEL_HEIGHT = 44
FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)


def main() -> None:
    for step, title in STEPS:
        _side_by_side(step=step, title=title)
    for column, _ in COLUMNS:
        _gif(column=column)


def _side_by_side(step: str, title: str) -> None:
    tiles = [_tile(column=column, label=label, step=step) for column, label in COLUMNS]
    width = sum(tile.width for tile in tiles)
    sheet = Image.new("RGB", (width, tiles[0].height + LABEL_HEIGHT), "white")
    ImageDraw.Draw(sheet).text((12, 8), title, fill="black", font=FONT)
    x = 0
    for tile in tiles:
        sheet.paste(tile, (x, LABEL_HEIGHT))
        x += tile.width
    sheet.save(HERE / f"side-by-side-{step}.jpg", quality=82)


def _tile(column: str, label: str, step: str) -> Image.Image:
    path = SHOTS / f"{column}-{step}.jpg"
    height = TILE_WIDTH * 900 // 1440
    tile = Image.new("RGB", (TILE_WIDTH, height + LABEL_HEIGHT), (40, 40, 40))
    if path.exists():
        tile.paste(Image.open(path).convert("RGB").resize((TILE_WIDTH, height)), (0, LABEL_HEIGHT))
        text = label
    else:
        # Main never refuses a box, so it has no "draw before picking" frame.
        text = f"{label}: no such step, the box goes to the default source"
    ImageDraw.Draw(tile).text((12, 8), text, fill="white", font=FONT)
    return tile


def _gif(column: str) -> None:
    frames = [
        Image.open(path).convert("RGB").resize((720, 450))
        for step, _ in STEPS
        if (path := SHOTS / f"{column}-{step}.jpg").exists()
    ]
    frames[0].save(
        HERE / f"{column}.gif", save_all=True, append_images=frames[1:], duration=1800, loop=0
    )


if __name__ == "__main__":
    main()
