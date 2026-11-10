"""Helpers for the training service tests."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.training_run import ACTIVE_TRAINING_RUN_STATUSES
from lightly_studio.resolvers import collection_resolver, tag_resolver
from lightly_studio.services.training_service.training_run_registry import TrainingRun
from lightly_studio.services.training_service.watch_training_run import SessionFactory
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)

# Writes a train log and one "cat" box per image, like the real runner does.
FAKE_RUNNER_SCRIPT = """
import json, sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text())
out_dir = Path(config["out_dir"])
out_dir.mkdir(parents=True)
(out_dir / "train.log").write_text("Train Step 2/2 | Epoch 0 | train_loss: 0.5000\\n")
images = json.loads(Path(config["predict_images_file"]).read_text())
predictions = [
    {
        "sample_id": image["sample_id"],
        "detections": [{"class_name": "cat", "bbox_xyxy": [10, 10, 30, 40], "score": 0.9}],
    }
    for image in images
]
Path(config["predictions_file"]).write_text(json.dumps(predictions))
"""


@dataclass
class TrainingDataset:
    """An image collection with a train tag, a val tag and a ground truth source "gt".

    Image 0 has the train tag, image 1 the val tag, image 2 has no tag. Images 0 and 1
    have one "cat" box each in "gt".
    """

    collection: CollectionTable
    images: list[ImageTable]
    train_tag_id: UUID
    val_tag_id: UUID
    gt_annotation_collection_id: UUID


def create_training_dataset(session: Session) -> TrainingDataset:
    """Create the dataset that `TrainingDataset` describes."""
    collection = create_collection(session=session)
    images = [
        create_image(
            session=session,
            collection_id=collection.collection_id,
            file_path_abs=f"/data/image_{index}.jpg",
            width=100,
            height=80,
        )
        for index in range(3)
    ]
    label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name="cat"
    )
    for image in images[:2]:
        create_annotation(
            session=session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_data={"x": 10, "y": 10, "width": 20, "height": 30},
            annotation_collection_name="gt",
        )
    gt_annotation_collection_id = collection_resolver.get_by_name(
        session=session, name="gt", parent_collection_id=collection.collection_id
    )
    assert gt_annotation_collection_id is not None
    return TrainingDataset(
        collection=collection,
        images=images,
        train_tag_id=_create_tag_with_samples(
            session=session, collection=collection, name="train", images=images[:1]
        ),
        val_tag_id=_create_tag_with_samples(
            session=session, collection=collection, name="val", images=images[1:2]
        ),
        gt_annotation_collection_id=gt_annotation_collection_id,
    )


def write_script(tmp_path: Path, content: str) -> Path:
    """Write a fake runner script and return its path."""
    script_path = tmp_path / "fake_runner.py"
    script_path.write_text(content, encoding="utf-8")
    return script_path


def session_factory_for(session: Session) -> SessionFactory:
    """Return a session factory that yields the test session."""

    @contextmanager
    def factory() -> Generator[Session, None, None]:
        yield session

    return factory


def wait_until_done(run: TrainingRun, timeout_s: float = 30.0) -> None:
    """Wait until the watcher thread of the run has set a final status."""
    deadline = time.monotonic() + timeout_s
    while run.status in ACTIVE_TRAINING_RUN_STATUSES:
        if time.monotonic() > deadline:
            raise TimeoutError(f"Training run is still '{run.status.value}'.")
        time.sleep(0.05)


def _create_tag_with_samples(
    session: Session, collection: CollectionTable, name: str, images: list[ImageTable]
) -> UUID:
    tag = create_tag(session=session, collection_id=collection.collection_id, tag_name=name)
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=tag.tag_id, sample_ids=[image.sample_id for image in images]
    )
    return tag.tag_id
