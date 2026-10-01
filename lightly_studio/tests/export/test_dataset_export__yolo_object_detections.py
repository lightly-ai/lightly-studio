"""Tests for exporting object detections to YOLO format via `DatasetExport`."""

from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation_label,
    create_collection,
    create_images,
)


class TestDatasetExport:
    def test_to_yolo_object_detections(
        self,
        db_session: Session,
        tmp_path: Path,
    ) -> None:
        """Tests exporting object detections to YOLO format."""
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="image0.jpg", width=100, height=100),
                ImageStub(path="image1.jpg", width=200, height=200),
            ],
        )
        label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="dog"
        )
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=images[0].sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    x=10,
                    y=10,
                    width=20,
                    height=40,
                ),
            ],
        )

        output_folder = tmp_path / "yolo"
        ImageDatasetExport(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
        ).to_yolo_object_detections(output_folder=output_folder, annotation_collection_id=None)

        # The dataset config lists the single category.
        with open(output_folder / "data.yaml") as f:
            data_yaml = yaml.safe_load(f)
        assert data_yaml == {"path": ".", "train": "images", "nc": 1, "names": {0: "dog"}}

        # One label file per image. The box (x=10, y=10, w=20, h=40) on a 100x100 image has
        # center (20, 30), so normalized cx=0.2 cy=0.3 w=0.2 h=0.4. image1 has no annotations.
        assert (output_folder / "labels" / "image0.txt").read_text() == "0 0.2 0.3 0.2 0.4\n"
        assert (output_folder / "labels" / "image1.txt").read_text() == ""

    def test_to_yolo_object_detections__filters_by_annotation_collection(
        self,
        db_session: Session,
        tmp_path: Path,
    ) -> None:
        """Annotations from other annotation collections are excluded from the export."""
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path="image0.jpg", width=100, height=100)],
        )
        label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="dog"
        )
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=images[0].sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    x=10,
                    y=10,
                    width=20,
                    height=40,
                ),
            ],
        )

        output_folder = tmp_path / "yolo"
        ImageDatasetExport(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
        ).to_yolo_object_detections(
            output_folder=output_folder, annotation_collection_id=uuid.uuid4()
        )

        # The annotation belongs to a different collection, so it is filtered out.
        assert (output_folder / "labels" / "image0.txt").read_text() == ""
