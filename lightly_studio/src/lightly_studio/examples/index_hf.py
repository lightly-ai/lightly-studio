"""Index a public Hugging Face image dataset.

Run with ``uv run --extra hugging-face src/lightly_studio/examples/index_gh.py``.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import datasets
import lightly_studio as ls
from lightly_studio.core.annotation import CreateObjectDetection
from lightly_studio.database import db_manager

HUGGING_FACE_REPOSITORY = "rishitdagli/cppe-5"
SPLIT = "train"
SAMPLE_LIMIT = 128
DATABASE_PATH = "hugging_face_example.db"
ANNOTATION_SOURCE = "ground-truth"
CLASS_NAMES = ("Coverall", "Face_Shield", "Gloves", "Goggles", "Mask")


def create_annotations(objects: Mapping[str, Any]) -> list[CreateObjectDetection]:
    """Convert CPPE-5 objects to LightlyStudio object detection annotations."""
    return [
        CreateObjectDetection(
            class_name=CLASS_NAMES[category],
            x=round(bbox[0]),
            y=round(bbox[1]),
            width=round(bbox[2]),
            height=round(bbox[3]),
        )
        for bbox, category in zip(objects["bbox"], objects["category"])
    ]


def add_annotations(
    dataset: ls.ImageDataset,
    annotation_rows: Sequence[Mapping[str, Any]],
) -> None:
    """Add the CPPE-5 annotations to their corresponding indexed images."""
    samples = sorted(dataset, key=lambda sample: sample.file_name)
    if len(samples) != len(annotation_rows):
        raise RuntimeError("The indexed image and annotation row counts do not match.")
    for sample, row in zip(samples, annotation_rows):
        sample.add_annotations(
            annotations=create_annotations(objects=row["objects"]),
            annotation_source=ANNOTATION_SOURCE,
        )


def main() -> None:
    """Index CPPE-5 images and object detection annotations, then start the GUI."""
    db_manager.connect(db_file=DATABASE_PATH, cleanup_existing=True)
    hugging_face_dataset = datasets.load_dataset(  # type: ignore[attr-defined]
        HUGGING_FACE_REPOSITORY,
        split=SPLIT,
        streaming=True,
    ).take(SAMPLE_LIMIT)
    annotation_rows = list(hugging_face_dataset.remove_columns("image"))

    dataset = ls.ImageDataset.create(name="hugging-face-cppe-5")
    dataset.add_images_from_hugging_face(
        hugging_face_dataset=hugging_face_dataset,
        images_path=Path("datasets") / "hugging-face-cppe-5",
    )
    add_annotations(dataset=dataset, annotation_rows=annotation_rows)
    ls.start_gui()


if __name__ == "__main__":
    main()
