"""Tests for the LightlyStudio label export adapter."""

from __future__ import annotations

from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import ImageObjectDetection, SingleObjectDetection
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export.lightly_studio_label_input import (
    LightlyStudioObjectDetectionInput,
)
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation_label,
    create_collection,
    create_images,
)


class TestLightlyStudioLabelInput:
    def test_get_categories(
        self,
        db_session: Session,
        dataset_with_annotations: CollectionTable,
    ) -> None:
        dataset = dataset_with_annotations

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        assert list(label_input.get_categories()) == [
            Category(id=0, name="cat"),
            Category(id=1, name="dog"),
            Category(id=2, name="zebra"),
        ]

    def test_get_categories__no_annotations(
        self,
        db_session: Session,
    ) -> None:
        dataset = create_collection(session=db_session)
        images = [
            ImageStub(path="img1", width=100, height=100),
            ImageStub(path="img2", width=200, height=200),
        ]
        create_images(db_session=db_session, collection_id=dataset.collection_id, images=images)
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        assert list(label_input.get_categories()) == []

    def test_get_images(
        self, db_session: Session, dataset_with_annotations: CollectionTable
    ) -> None:
        dataset = dataset_with_annotations

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        assert list(label_input.get_images()) == [
            Image(id=0, filename="img1", width=100, height=100),
            Image(id=1, filename="img2", width=200, height=200),
            Image(id=2, filename="img3", width=300, height=300),
        ]

    def test_get_images__no_images(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        assert list(label_input.get_images()) == []

    def test_get_labels(
        self, db_session: Session, dataset_with_annotations: CollectionTable
    ) -> None:
        dataset = dataset_with_annotations

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        labels = list(label_input.get_labels())

        # There are 3 samples
        assert len(labels) == 3
        assert labels[0] == ImageObjectDetection(
            image=Image(id=0, filename="img1", width=100, height=100),
            objects=[
                SingleObjectDetection(
                    category=Category(id=1, name="dog"),
                    box=BoundingBox(xmin=10, ymin=10, xmax=20, ymax=20),
                    confidence=None,
                ),
                SingleObjectDetection(
                    category=Category(id=0, name="cat"),
                    box=BoundingBox(xmin=20, ymin=20, xmax=40, ymax=40),
                    confidence=2 / 8,
                ),
            ],
        )
        assert labels[1] == ImageObjectDetection(
            image=Image(id=1, filename="img2", width=200, height=200),
            objects=[
                SingleObjectDetection(
                    category=Category(id=1, name="dog"),
                    box=BoundingBox(xmin=30, ymin=30, xmax=60, ymax=60),
                    confidence=3 / 8,
                ),
            ],
        )
        assert labels[2] == ImageObjectDetection(
            image=Image(id=2, filename="img3", width=300, height=300),
            objects=[],
        )

    def test_get_labels__no_annotations(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        images = [
            ImageStub(path="img1", width=100, height=100),
            ImageStub(path="img2", width=200, height=200),
        ]
        create_images(db_session=db_session, collection_id=dataset.collection_id, images=images)

        # Test for task_no_ann
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        labels = list(label_input.get_labels())

        # There are 2 samples
        assert len(labels) == 2
        assert labels[0] == ImageObjectDetection(
            image=Image(id=0, filename="img1", width=100, height=100),
            objects=[],
        )
        assert labels[1] == ImageObjectDetection(
            image=Image(id=1, filename="img2", width=200, height=200),
            objects=[],
        )

    def test_get_labels__instance_segmentation(self, db_session: Session) -> None:
        """We currently export only object detection annotations, not instance segmentation."""
        dataset = create_collection(session=db_session)
        images_to_create = [
            ImageStub(path="img1", width=100, height=100),
            ImageStub(path="img2", width=200, height=200),
        ]
        images = create_images(
            db_session=db_session, collection_id=dataset.collection_id, images=images_to_create
        )
        dog_label = create_annotation_label(
            session=db_session, root_dataset_id=dataset.dataset_id, label_name="dog"
        )
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=dataset.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=images[0].sample_id,
                    annotation_label_id=dog_label.annotation_label_id,
                    annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                    confidence=None,
                    x=50,
                    y=50,
                    width=50,
                    height=50,
                    segmentation_mask=[1000, 500, 1000],
                ),
            ],
        )
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            samples=DatasetQuery(dataset=dataset, session=db_session),
        )
        labels = list(label_input.get_labels())

        # There are 2 samples
        assert len(labels) == 2
        assert labels[0] == ImageObjectDetection(
            image=Image(id=0, filename="img1", width=100, height=100),
            objects=[],
        )
        assert labels[1] == ImageObjectDetection(
            image=Image(id=1, filename="img2", width=200, height=200),
            objects=[],
        )
