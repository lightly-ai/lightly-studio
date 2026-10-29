"""Workflow step f, local: load model_v1 predictions as annotation source `model_v1`.

Local counterpart of .experimental/ux-iteration/train/import_model_v1.py, which loaded them into
hosted from S3. Stop the GUI first: DuckDB allows one writer.

Usage:
    python import_predictions.py --db ~/data/caltech-ux-run-dbs/prototype.db
"""

from __future__ import annotations

import argparse
from pathlib import Path

import lightly_studio as ls
from lightly_studio.database import db_manager

PREDICTIONS = Path(
    "/Users/gabrielfruet/dev/lightly/lightly-studio/.experimental/ux-iteration/train/"
    "model_v1_predictions.json"
)

parser = argparse.ArgumentParser()
parser.add_argument("--db", type=str, required=True)
parser.add_argument("--data", type=Path, default=Path("~/data/caltech-ux-run"))
parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
args = parser.parse_args()

db_manager.connect(db_file=args.db, must_exist=True)
dataset = ls.ImageDataset.load("caltech-ux-run")
dataset.add_annotations_from_coco(
    annotations_json=args.predictions,
    images_root=args.data.expanduser() / "images",
    annotation_source="model_v1",
)
