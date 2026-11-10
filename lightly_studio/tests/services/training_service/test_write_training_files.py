from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.services.training_service import write_training_files
from lightly_studio.services.training_service.training_run_files import TrainingRunFiles
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_image
from tests.services.training_service import helpers


def test_write_training_files(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    # An annotation in a different source must not reach the training data.
    label = create_annotation_label(
        session=db_session, root_collection_id=dataset.collection.collection_id, label_name="dog"
    )
    create_annotation(
        session=db_session,
        collection_id=dataset.collection.collection_id,
        sample_id=dataset.images[0].sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="predictions",
    )
    files = TrainingRunFiles(run_dir=tmp_path / "run")

    write_training_files.write_training_files(
        session=db_session,
        collection=dataset.collection,
        files=files,
        train_sample_ids=[dataset.images[0].sample_id],
        val_sample_ids=[dataset.images[1].sample_id],
        gt_annotation_collection_id=dataset.gt_annotation_collection_id,
        model_name="model-a",
        steps=7,
    )

    train_coco = json.loads(files.train_annotations_file.read_text())
    assert [image["file_name"] for image in train_coco["images"]] == ["/data/image_0.jpg"]
    assert [(i["width"], i["height"]) for i in train_coco["images"]] == [(100, 80)]
    assert [a["bbox"] for a in train_coco["annotations"]] == [[10.0, 10.0, 20.0, 30.0]]
    val_coco = json.loads(files.val_annotations_file.read_text())
    assert [image["file_name"] for image in val_coco["images"]] == ["/data/image_1.jpg"]
    predict_images = json.loads(files.predict_images_file.read_text())
    assert sorted(entry["path"] for entry in predict_images) == [
        "/data/image_0.jpg",
        "/data/image_1.jpg",
        "/data/image_2.jpg",
    ]
    config = json.loads(files.config_file.read_text())
    assert config["model_name"] == "model-a"
    assert config["steps"] == 7
    assert config["out_dir"] == str(files.out_dir)


def test_write_training_files__no_train_annotations(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)

    with pytest.raises(ValueError, match="no annotations in the ground truth source"):
        write_training_files.write_training_files(
            session=db_session,
            collection=dataset.collection,
            files=TrainingRunFiles(run_dir=tmp_path / "run"),
            # Image 2 has no ground truth annotations.
            train_sample_ids=[dataset.images[2].sample_id],
            val_sample_ids=[dataset.images[1].sample_id],
            gt_annotation_collection_id=dataset.gt_annotation_collection_id,
            model_name="model-a",
            steps=7,
        )


def test_write_training_files__remote_image(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    create_image(
        session=db_session,
        collection_id=dataset.collection.collection_id,
        file_path_abs="s3://bucket/image_3.jpg",
    )

    with pytest.raises(ValueError, match="1 images are remote"):
        write_training_files.write_training_files(
            session=db_session,
            collection=dataset.collection,
            files=TrainingRunFiles(run_dir=tmp_path / "run"),
            train_sample_ids=[dataset.images[0].sample_id],
            val_sample_ids=[dataset.images[1].sample_id],
            gt_annotation_collection_id=dataset.gt_annotation_collection_id,
            model_name="model-a",
            steps=7,
        )
