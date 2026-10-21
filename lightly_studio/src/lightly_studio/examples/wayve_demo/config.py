"""Shared settings for the Wayve demo scripts.

All scripts use the same Postgres database as the GUI. Start it with:

    docker start wayve-postgres

Set `WAYVE_DB_URL` to use a different database.
"""

from __future__ import annotations

import os
from pathlib import Path

from lightly_studio.database import db_manager

DB_URL = os.environ.get("WAYVE_DB_URL", "postgresql://lightly:lightly@localhost:5434/wayve")

DATA_DIR = Path.home() / "demo_data/wayve"
NEXAR_DIR = DATA_DIR / "nexar"
VIDEOS_DIR = NEXAR_DIR / "videos"
FRAMES_DIR = NEXAR_DIR / "frames"
YOLO_WEIGHTS = DATA_DIR / "yolo11n.pt"

CLIPS_DATASET = "nexar-clips"
FRAMES_DATASET = "nexar-frames"


def connect(cleanup_existing: bool = False) -> None:
    """Connect to the demo database.

    Args:
        cleanup_existing: Drop all tables first. Only `build_dataset.py` sets this.
    """
    db_manager.connect(db_url=DB_URL, cleanup_existing=cleanup_existing)
