"""Join the capture.cjs screenshots into side-by-side sheets and one GIF per column.

The screenshots are 2880x1800 (1440x900 at 2x). Each sheet keeps them sharp:
- `side-by-side-<step>.png`: the full window of each column, 1440 px wide per column.
- `panel-<step>.png`: the Annotations panel of each column at full 2x resolution.
"""

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
    ("1-edit-mode", "1. Open the sample, click Edit"),
    ("2-draw-before-pick", "2. Draw a box before picking a source"),
    ("3-picked-model_v2", "3. Pick model_v2"),
    ("4-deer-box-in-model_v2", "4. Draw the deer box"),
    ("5-classification", "5. The Classification \"+\""),
]
# The Annotations panel in a 1440x900 window, in 2x pixels: left, top, right, bottom.
PANEL_BOX = (2064, 330, 2816, 1760)
FULL_TILE_WIDTH = 1440
LABEL_HEIGHT = 72
FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
GAP = 16


def main() -> None:
    for step, title in STEPS:
        _sheet(step=step, title=title, name="side-by-side", crop=None)
        _sheet(step=step, title=title, name="panel", crop=PANEL_BOX)
    for column, _ in COLUMNS:
        _gif(column=column)


def _sheet(step: str, title: str, name: str, crop: tuple[int, int, int, int] | None) -> None:
    tiles = [_tile(column=column, label=label, step=step, crop=crop) for column, label in COLUMNS]
    width = sum(tile.width for tile in tiles) + GAP * (len(tiles) - 1)
    sheet = Image.new("RGB", (width, tiles[0].height + LABEL_HEIGHT), "white")
    ImageDraw.Draw(sheet).text((16, 14), title, fill="black", font=FONT)
    x = 0
    for tile in tiles:
        sheet.paste(tile, (x, LABEL_HEIGHT))
        x += tile.width + GAP
    sheet.save(HERE / f"{name}-{step}.png", optimize=True)


def _tile(
    column: str, label: str, step: str, crop: tuple[int, int, int, int] | None
) -> Image.Image:
    path = SHOTS / f"{column}-{step}.png"
    if crop is None:
        size = (FULL_TILE_WIDTH, FULL_TILE_WIDTH * 900 // 1440)
    else:
        size = (crop[2] - crop[0], crop[3] - crop[1])
    tile = Image.new("RGB", (size[0], size[1] + LABEL_HEIGHT), (40, 40, 40))
    if path.exists():
        image = Image.open(path).convert("RGB")
        image = image.crop(crop) if crop else image.resize(size, Image.Resampling.LANCZOS)
        tile.paste(image, (0, LABEL_HEIGHT))
        text = label
    else:
        # Main never refuses a box, so it has no "draw before picking" frame.
        text = f"{label}: no such step"
    ImageDraw.Draw(tile).text((16, 14), text, fill="white", font=FONT)
    return tile


def _gif(column: str) -> None:
    frames = [
        Image.open(path).convert("RGB").resize((1440, 900), Image.Resampling.LANCZOS)
        for step, _ in STEPS
        if (path := SHOTS / f"{column}-{step}.png").exists()
    ]
    frames[0].save(
        HERE / f"{column}.gif", save_all=True, append_images=frames[1:], duration=2000, loop=0
    )


if __name__ == "__main__":
    main()
