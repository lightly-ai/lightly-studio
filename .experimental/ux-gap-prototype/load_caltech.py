"""Load the Caltech UX-run subset into a local LightlyStudio DuckDB file.

Copy of .experimental/ux-iteration/datasets/load_caltech.py from the main checkout, with the
per-sample metadata loop replaced by the bulk call (the loop takes ~9 minutes, friction row 1).
Both the `main` baseline and the prototype load with this file, so their data is identical.

Usage:
    python load_caltech.py --data ~/data/caltech-ux-run --db caltech.db [--no-embed] [--with-gt]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import lightly_studio as ls
from lightly_studio.database import db_manager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--db", type=str, required=True)
    parser.add_argument("--no-embed", action="store_true")
    parser.add_argument("--with-gt", action="store_true")
    args = parser.parse_args()
    data: Path = args.data.expanduser()
    embed = not args.no_embed

    db_manager.connect(db_file=args.db, cleanup_existing=True)
    dataset = ls.ImageDataset.load_or_create("caltech-ux-run")
    dataset.add_images_from_path(path=data / "images", embed=embed)

    metadata = json.loads((data / "metadata.json").read_text())
    dataset.update_metadata(
        [(sample.sample_id, metadata[sample.file_name]) for sample in dataset]
    )

    dataset.add_annotations_from_coco(
        annotations_json=data / "labels_noisy.json",
        images_root=data / "images",
        annotation_source="labels",
        embed_annotations=embed,
    )
    if args.with_gt:
        for split in ("labeled", "unlabeled", "test"):
            dataset.add_annotations_from_coco(
                annotations_json=data / f"gt_{split}.json",
                images_root=data / "images",
                annotation_source="gt",
                embed_annotations=embed,
            )
    print("loaded", len(list(dataset)), "images")


if __name__ == "__main__":
    main()
