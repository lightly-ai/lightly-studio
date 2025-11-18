"""Tests for annotation details functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
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


def test_instance_segmentation_details(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that object detection details are correctly loaded."""
    annotations = annotation_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_types=[AnnotationType.INSTANCE_SEGMENTATION]),
    ).annotations

    for annotation in annotations:
        assert annotation.instance_segmentation_details is not None
        assert annotation.instance_segmentation_details.x == 15.0
        assert annotation.instance_segmentation_details.y == 25.0
        assert annotation.instance_segmentation_details.width == 150.0
        assert annotation.instance_segmentation_details.height == 250.0
        assert annotation.instance_segmentation_details.segmentation_mask == [
            1,
            2,
            3,
            4,
        ]


def test_semantic_segmentation_details(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that object detection details are correctly loaded."""
    annotations = annotation_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_types=[AnnotationType.SEMANTIC_SEGMENTATION]),
    ).annotations

    for annotation in annotations:
        assert annotation.semantic_segmentation_details is not None
        assert annotation.semantic_segmentation_details.segmentation_mask == [
            5,
            6,
            7,
            8,
        ]


def test_default_ordering_by_file_path_abs(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that annotations are ordered by sample file path."""
    annotations = annotation_resolver.get_all(db_session).annotations

    sample_paths: list[str] = [
        a.sample.image.file_path_abs
        for a in annotations
        if a.sample is not None and a.sample.image is not None
    ]
    assert len(sample_paths) == len(annotations), "Not all annotations have a sample file path."
    assert sample_paths == sorted(sample_paths)
