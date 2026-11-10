"""Example of how to train a human and animal detector from the GUI with LightlyTrain.

The example adds the COCO samples with two annotation classes, "human" and "animal", in the
annotation source "ground_truth". It tags 60 % of the images "train" and 20 % "val". The other
20 % have no tag and no annotations: they are the images to label later. Then it starts the GUI.
In the GUI, open "Menu > Train model".

Training needs LightlyTrain. Install it in the Python of LightlyStudio, or set
LIGHTLY_STUDIO_TRAINING_PYTHON to a Python that has it.
"""

from __future__ import annotations

import json
import random
import tempfile
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any

from environs import Env

import lightly_studio as ls
from lightly_studio.database import db_manager

HUMAN_CATEGORY_ID = 1
ANIMAL_CATEGORY_ID = 2
TRAIN_FRACTION = 0.6
VAL_FRACTION = 0.2

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path("EXAMPLES_COCO_JSON_PATH")
images_path = env.path("EXAMPLES_COCO_IMAGES_PATH")


def main() -> None:
    """Add the samples with human and animal boxes, tag them and start the GUI."""
    coco = json.loads(annotations_json.read_text(encoding="utf-8"))
    split = _split_file_names(file_names=[image["file_name"] for image in coco["images"]])
    unlabeled_file_names = {name for name, tag in split.items() if tag is None}

    dataset = ls.ImageDataset.create()
    with tempfile.TemporaryDirectory() as temp_dir:
        human_animal_json = Path(temp_dir) / "human_animal.json"
        _write_human_animal_coco(
            coco=coco, unlabeled_file_names=unlabeled_file_names, target=human_animal_json
        )
        dataset.add_samples_from_coco(
            annotations_json=human_animal_json,
            images_path=images_path,
            annotation_source="ground_truth",
        )

    for sample in dataset.query().to_list():
        tag = split[sample.file_name]
        if tag is not None:
            sample.add_tag(tag)

    tag_names = list(split.values())
    print(
        f"Tagged {tag_names.count('train')} images 'train' and {tag_names.count('val')} "
        f"images 'val'. {len(unlabeled_file_names)} images have no tag and no annotations.\n"
        "In the GUI, open 'Menu > Train model' and select the tags and 'ground_truth'."
    )
    ls.start_gui()


def _split_file_names(file_names: Sequence[str]) -> dict[str, str | None]:
    """Assign each image to "train", "val" or no tag (None).

    A fixed seed gives the same split each time.
    """
    shuffled = sorted(file_names)
    random.Random(0).shuffle(shuffled)
    train_count = round(TRAIN_FRACTION * len(shuffled))
    val_count = round(VAL_FRACTION * len(shuffled))
    split: dict[str, str | None] = {}
    for index, file_name in enumerate(shuffled):
        if index < train_count:
            split[file_name] = "train"
        elif index < train_count + val_count:
            split[file_name] = "val"
        else:
            split[file_name] = None
    return split


def _write_human_animal_coco(
    coco: dict[str, Any], unlabeled_file_names: Collection[str], target: Path
) -> None:
    """Write a copy of COCO data with only the classes "human" and "animal".

    "person" becomes "human". All classes of the COCO supercategory "animal" become
    "animal". Annotations of other classes and of the unlabeled images are removed. All
    images are kept, so images without humans and animals are negative examples.
    """
    new_category_ids = {
        category["id"]: new_id
        for category in coco["categories"]
        if (new_id := _new_category_id(category=category)) is not None
    }
    unlabeled_image_ids = {
        image["id"] for image in coco["images"] if image["file_name"] in unlabeled_file_names
    }
    annotations = [
        {**annotation, "category_id": new_category_ids[annotation["category_id"]]}
        for annotation in coco["annotations"]
        if annotation["category_id"] in new_category_ids
        and annotation["image_id"] not in unlabeled_image_ids
    ]
    categories = [
        {"id": HUMAN_CATEGORY_ID, "name": "human", "supercategory": "human"},
        {"id": ANIMAL_CATEGORY_ID, "name": "animal", "supercategory": "animal"},
    ]
    target.write_text(
        json.dumps({**coco, "categories": categories, "annotations": annotations}),
        encoding="utf-8",
    )


def _new_category_id(category: dict[str, Any]) -> int | None:
    if category["name"] == "person":
        return HUMAN_CATEGORY_ID
    if category.get("supercategory") == "animal":
        return ANIMAL_CATEGORY_ID
    return None


if __name__ == "__main__":
    main()
