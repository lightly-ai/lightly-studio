"""Add 6 synthetic annotation sources to a Caltech DB, for demoing the source and class filter.

Derived from the real `labels` (labels_noisy.json) and `model_v1` predictions, so the counts
look plausible. Together with `labels` and `model_v1` the DB has 8 annotation sources.
Stop the GUI first: DuckDB allows one writer.

Usage:
    python add_demo_sources.py --db ~/data/caltech-ux-run-dbs/demo.db
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import tempfile
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
args = parser.parse_args()
data = args.data.expanduser()

predictions = json.loads(PREDICTIONS.read_text())
labels = json.loads((data / "labels_noisy.json").read_text())
rng = random.Random(0)


def with_annotations(coco: dict, annotations: list[dict]) -> dict:
    out = {k: v for k, v in coco.items() if k != "annotations"}
    out["annotations"] = annotations
    return out


def jitter(annotation: dict, fraction: float) -> dict:
    a = copy.deepcopy(annotation)
    x, y, w, h = a["bbox"]
    dx, dy = rng.uniform(-fraction, fraction) * w, rng.uniform(-fraction, fraction) * h
    a["bbox"] = [max(0.0, x + dx), max(0.0, y + dy), w, h]
    return a


def swap_some(annotations: list[dict], share: float, category_ids: list[int]) -> list[dict]:
    out = []
    for annotation in annotations:
        a = copy.deepcopy(annotation)
        if rng.random() < share:
            a["category_id"] = rng.choice(category_ids)
        out.append(a)
    return out


def image_slice(coco: dict, start: float, end: float) -> list[dict]:
    image_ids = sorted(image["id"] for image in coco["images"])
    keep = set(image_ids[int(start * len(image_ids)) : int(end * len(image_ids))])
    return [a for a in coco["annotations"] if a["image_id"] in keep]


category_ids = [c["id"] for c in predictions["categories"]]
pred = predictions["annotations"]
sam = with_annotations(predictions, [{**a, "category_id": 1} for a in pred])
sam["categories"] = [{"id": 1, "name": "animal"}]

sources = {
    "model_v2": with_annotations(predictions, [jitter(a, 0.03) for a in pred if a["score"] >= 0.5]),
    "model_v3": with_annotations(predictions, [a for a in pred if a["score"] >= 0.7]),
    "model_v4": with_annotations(predictions, swap_some(pred, 0.1, category_ids)),
    "review_round_1": with_annotations(labels, image_slice(labels, 0.0, 0.4)),
    "review_round_2": with_annotations(labels, image_slice(labels, 0.4, 0.7)),
    "sam_auto": sam,
}

db_manager.connect(db_file=args.db, must_exist=True)
dataset = ls.ImageDataset.load("caltech-ux-run")
with tempfile.TemporaryDirectory() as tmp:
    for name, coco in sources.items():
        path = Path(tmp) / f"{name}.json"
        path.write_text(json.dumps(coco))
        print(f"{name}: {len(coco['annotations'])} annotations")
        dataset.add_annotations_from_coco(
            annotations_json=path,
            images_root=data / "images",
            annotation_source=name,
        )
