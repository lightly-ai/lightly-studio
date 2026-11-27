"""Serve a small COCO val2017 image dataset to try browser auto-labeling.

Run from `lightly_studio/`:

    uv run python ../.experimental/browser-auto-labeling/demo_dataset.py

Then start the frontend dev server against port 8021.
"""

from __future__ import annotations

from pathlib import Path

import lightly_studio as ls
from lightly_studio.database import db_manager

COCO_VAL_DIR = Path.home() / "data/coco2017/val2017"
IMAGES_DIR = Path(__file__).parent / "images"
DB_FILE = Path(__file__).parent / "demo.db"
NUM_IMAGES = 200
PORT = 8021


def main() -> None:
    """Link the first COCO val images, index them without embeddings and start the server."""
    IMAGES_DIR.mkdir(exist_ok=True)
    for source in sorted(COCO_VAL_DIR.glob("*.jpg"))[:NUM_IMAGES]:
        link = IMAGES_DIR / source.name
        if not link.exists():
            link.symlink_to(source)
    db_manager.connect(db_file=str(DB_FILE), cleanup_existing=True)
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=IMAGES_DIR, embed=False)
    ls.start_gui(port=PORT, open_browser=False)


if __name__ == "__main__":
    main()
