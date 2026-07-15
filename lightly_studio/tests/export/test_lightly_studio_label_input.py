"""Tests for the LightlyStudio label export adapter."""

from __future__ import annotations

from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import ImageObjectDetection, SingleObjectDetection
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export import image_dataset_export
from lightly_studio.export.lightly_studio_label_input import (
    LightlyStudioObjectDetectionInput,
    LightlyStudioPascalVOCInstanceSegmentationInput,
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_images,
)


class TestLightlyStudioLabelInput:
    def test_get_categories(
        self,
        db_session: Session,
        collection_with_annotations: CollectionTable,
    ) -> None:
        collection = collection_with_annotations

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input.get_categories()) == [
            Category(id=0, name="cat"),
            Category(id=1, name="dog"),
            Category(id=2, name="zebra"),
        ]

    def test_get_categories__pascalvoc_segmentation_mask_starts_with_one(
        self,
        db_session: Session,
        collection_with_annotations: CollectionTable,
    ) -> None:
        collection = collection_with_annotations

        label_input = LightlyStudioPascalVOCInstanceSegmentationInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input.get_categories()) == [
            Category(id=1, name="cat"),
            Category(id=2, name="dog"),
            Category(id=3, name="zebra"),
        ]

    def test_get_categories__no_annotations(
        self,
        db_session: Session,
    ) -> None:
        collection = create_collection(session=db_session)
        images = [
            ImageStub(path="img1", width=100, height=100),
            ImageStub(path="img2", width=200, height=200),
        ]
        create_images(db_session=db_session, collection_id=collection.collection_id, images=images)
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input.get_categories()) == []

    def test_get_images(
        self, db_session: Session, collection_with_annotations: CollectionTable
    ) -> None:
        collection = collection_with_annotations

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input.get_images()) == [
            Image(id=0, filename="img1", width=100, height=100),
            Image(id=1, filename="img2", width=200, height=200),
            Image(id=2, filename="img3", width=300, height=300),
        ]

    def test_get_images__no_images(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input.get_images()) == []

    def test_get_labels(
        self, db_session: Session, collection_with_annotations: CollectionTable
    ) -> None:
        collection = collection_with_annotations

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
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
        collection = create_collection(session=db_session)
        images = [
            ImageStub(path="img1", width=100, height=100),
            ImageStub(path="img2", width=200, height=200),
        ]
        create_images(db_session=db_session, collection_id=collection.collection_id, images=images)

        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
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

    def test_get_labels__annotation_collection_id(self, db_session: Session) -> None:
        """Only annotations from the specified collection are exported."""
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs="img1",
            width=100,
            height=100,
        )
        dog_label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="dog"
        )
        cat_label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="cat"
        )
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=dog_label.annotation_label_id,
            annotation_collection_name="source_1",
            annotation_data={"x": 10, "y": 10, "width": 10, "height": 10},
        )
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_collection_name="source_2",
            annotation_data={"x": 20, "y": 20, "width": 20, "height": 20},
        )
        source_1_id = collection_resolver.get_or_create_child_collection(
            session=db_session,
            collection_id=collection.collection_id,
            sample_type=SampleType.ANNOTATION,
            name="source_1",
        )
        source_2_id = collection_resolver.get_or_create_child_collection(
            session=db_session,
            collection_id=collection.collection_id,
            sample_type=SampleType.ANNOTATION,
            name="source_2",
        )

        # cat=id_0, dog=id_1 (categories are sorted alphabetically)
        label_input_source_1 = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=source_1_id,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input_source_1.get_labels()) == [
            ImageObjectDetection(
                image=Image(id=0, filename="img1", width=100, height=100),
                objects=[
                    SingleObjectDetection(
                        category=Category(id=1, name="dog"),
                        box=BoundingBox(xmin=10, ymin=10, xmax=20, ymax=20),
                        confidence=None,
                    )
                ],
            )
        ]

        label_input_source_2 = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=source_2_id,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        assert list(label_input_source_2.get_labels()) == [
            ImageObjectDetection(
                image=Image(id=0, filename="img1", width=100, height=100),
                objects=[
                    SingleObjectDetection(
                        category=Category(id=0, name="cat"),
                        box=BoundingBox(xmin=20, ymin=20, xmax=40, ymax=40),
                        confidence=None,
                    )
                ],
            )
        ]

    def test_get_labels__annotation_collection_id_none_with_multiple_sources(
        self, db_session: Session
    ) -> None:
        """Annotations from all collections are exported when annotation_collection_id is None."""
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs="img1",
            width=100,
            height=100,
        )
        dog_label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="dog"
        )
        cat_label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="cat"
        )
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=dog_label.annotation_label_id,
            annotation_collection_name="source_1",
            annotation_data={"x": 10, "y": 10, "width": 10, "height": 10},
        )
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_collection_name="source_2",
            annotation_data={"x": 20, "y": 20, "width": 20, "height": 20},
        )

        # cat=id_0, dog=id_1 (categories are sorted alphabetically)
        label_input = LightlyStudioObjectDetectionInput(
            session=db_session,
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
        )
        labels = list(label_input.get_labels())
        assert len(labels) == 1
        assert labels[0].image == Image(id=0, filename="img1", width=100, height=100)
        # cat=id_0, dog=id_1 (categories are sorted alphabetically)
        assert sorted(labels[0].objects, key=lambda o: o.category.name) == [
            SingleObjectDetection(
                category=Category(id=0, name="cat"),
                box=BoundingBox(xmin=20, ymin=20, xmax=40, ymax=40),
                confidence=None,
            ),
            SingleObjectDetection(
                category=Category(id=1, name="dog"),
                box=BoundingBox(xmin=10, ymin=10, xmax=20, ymax=20),
                confidence=None,
            ),
        ]

    def test_get_labels__segmentation_mask(self, db_session: Session) -> None:
        """We currently export only object detection annotations, not segmentation mask."""
        collection = create_collection(session=db_session)
        images_to_create = [
            ImageStub(path="img1", width=100, height=100),
            ImageStub(path="img2", width=200, height=200),
        ]
        images = create_images(
            db_session=db_session, collection_id=collection.collection_id, images=images_to_create
        )
        dog_label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name="dog"
        )
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=images[0].sample_id,
                    annotation_label_id=dog_label.annotation_label_id,
                    annotation_type=AnnotationType.SEGMENTATION_MASK,
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
            dataset_id=collection.dataset_id,
            samples=DatasetQuery(dataset=collection, session=db_session),
            annotation_collection_id=None,
            sample_to_image=image_dataset_export.image_sample_to_image,
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
