"""Tests for annotation details functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_images,
)


def test_object_detection_details(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that object detection details are correctly loaded."""
    annotations = annotation_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_types=[AnnotationType.OBJECT_DETECTION]),
    ).annotations

    for annotation in annotations:
        assert annotation.object_detection_details is not None
        assert annotation.object_detection_details.x == 10.0
        assert annotation.object_detection_details.y == 20.0
        assert annotation.object_detection_details.width == 100.0
        assert annotation.object_detection_details.height == 200.0


def test_segmentation_details(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that object detection details are correctly loaded."""
    annotations = annotation_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_types=[AnnotationType.INSTANCE_SEGMENTATION]),
    ).annotations

    for annotation in annotations:
        assert annotation.segmentation_details is not None
        assert annotation.segmentation_details.x == 15.0
        assert annotation.segmentation_details.y == 25.0
        assert annotation.segmentation_details.width == 150.0
        assert annotation.segmentation_details.height == 250.0
        assert annotation.segmentation_details.segmentation_mask == [
            1,
            2,
            3,
            4,
        ]


def test_semantic_segmentation_details(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that semantic segmentation details are correctly loaded."""
    annotations = annotation_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_types=[AnnotationType.SEMANTIC_SEGMENTATION]),
    ).annotations

    for annotation in annotations:
        assert annotation.segmentation_details is not None
        assert annotation.segmentation_details.x == 17.0
        assert annotation.segmentation_details.y == 27.0
        assert annotation.segmentation_details.width == 170.0
        assert annotation.segmentation_details.height == 270.0
        assert annotation.segmentation_details.segmentation_mask == [
            5,
            6,
            7,
            8,
        ]


def test_default_ordering_by_file_path_abs(
    db_session: Session, collection: CollectionTable
) -> None:
    """Test that annotations are ordered by sample file path."""
    annotation_label = create_annotation_label(
        session=db_session,
        dataset_id=collection.collection_id,
        label_name="cat",
    )
    # Create samples in random order.
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="c/path/to/sample_3.jpg"),
            ImageStub(path="a/path/to/sample_1.jpg"),
            ImageStub(path="b/path/to/sample_2.jpg"),
        ],
    )
    # Create annotations for each sample.
    for img in images:
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=img.sample_id,
            annotation_label_id=annotation_label.annotation_label_id,
        )
    annotations = annotation_resolver.get_all(db_session).annotations

    # Verify that annotations are ordered by sample file path.
    assert len(annotations) == 3
    assert annotations[0].parent_sample_id == images[1].sample_id
    assert annotations[1].parent_sample_id == images[2].sample_id
    assert annotations[2].parent_sample_id == images[0].sample_id
