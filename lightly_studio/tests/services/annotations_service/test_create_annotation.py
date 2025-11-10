"""Tests for create_annotation service method."""

from __future__ import annotations

from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.services.annotations_service.create_annotation import (
    AnnotationCreateParams,
    create_annotation,
)


def test_create_annotation_object_detection(
    db_session: Session,
    dataset_id: UUID,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Test to create object detection annotation."""
    annotation = AnnotationCreateParams(
        annotation_label_id=annotation_labels[0].annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        dataset_id=dataset_id,
        parent_sample_id=samples[0].sample_id,
        x=100,
        y=50,
        width=200,
        height=150,
    )
    result = create_annotation(session=db_session, annotation=annotation)

    # Verify the result
    assert isinstance(result, AnnotationBaseTable)
    assert result.annotation_label_id == annotation.annotation_label_id
    assert result.annotation_type == annotation.annotation_type
    assert result.dataset_id == annotation.dataset_id
    assert result.parent_sample_id == annotation.parent_sample_id
    assert result.object_detection_details is not None
    assert result.object_detection_details.x == annotation.x
    assert result.object_detection_details.y == annotation.y
    assert result.object_detection_details.width == annotation.width
    assert result.object_detection_details.height == annotation.height
    assert result.instance_segmentation_details is None
    assert result.semantic_segmentation_details is None


def test_create_annotation_instance_segmentation(
    db_session: Session,
    dataset_id: UUID,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Test to create instance segmentation annotation."""
    annotation = AnnotationCreateParams(
        annotation_label_id=annotation_labels[0].annotation_label_id,
        annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
        dataset_id=dataset_id,
        parent_sample_id=samples[0].sample_id,
        x=101,
        y=51,
        width=201,
        height=152,
        segmentation_mask=[1, 0, 0, 1, 1, 0],
    )
    result = create_annotation(session=db_session, annotation=annotation)

    assert isinstance(result, AnnotationBaseTable)
    assert result.annotation_label_id == annotation.annotation_label_id
    assert result.annotation_type == annotation.annotation_type
    assert result.dataset_id == annotation.dataset_id
    assert result.parent_sample_id == annotation.parent_sample_id
    assert result.instance_segmentation_details is not None
    assert result.instance_segmentation_details.x == annotation.x
    assert result.instance_segmentation_details.y == annotation.y
    assert result.instance_segmentation_details.width == annotation.width
    assert result.instance_segmentation_details.height == annotation.height
    assert result.instance_segmentation_details.segmentation_mask == annotation.segmentation_mask
    assert result.object_detection_details is None
    assert result.semantic_segmentation_details is None


def test_create_annotation_semantic_segmentation(
    db_session: Session,
    dataset_id: UUID,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Test to create semantic segmentation annotation."""
    annotation = AnnotationCreateParams(
        annotation_label_id=annotation_labels[0].annotation_label_id,
        annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
        dataset_id=dataset_id,
        parent_sample_id=samples[0].sample_id,
        segmentation_mask=[1, 0, 0, 1, 1, 0],
    )
    result = create_annotation(session=db_session, annotation=annotation)

    assert isinstance(result, AnnotationBaseTable)
    assert result.annotation_label_id == annotation.annotation_label_id
    assert result.annotation_type == annotation.annotation_type
    assert result.dataset_id == annotation.dataset_id
    assert result.parent_sample_id == annotation.parent_sample_id
    assert result.semantic_segmentation_details is not None
    assert result.semantic_segmentation_details.segmentation_mask == annotation.segmentation_mask
    assert result.instance_segmentation_details is None
    assert result.object_detection_details is None


def test_create_annotation_classification(
    db_session: Session,
    dataset_id: UUID,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Test to create classification annotation."""
    annotation = AnnotationCreateParams(
        annotation_label_id=annotation_labels[0].annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        dataset_id=dataset_id,
        parent_sample_id=samples[0].sample_id,
    )
    result = create_annotation(session=db_session, annotation=annotation)

    assert isinstance(result, AnnotationBaseTable)
    assert result.annotation_label_id == annotation.annotation_label_id
    assert result.annotation_type == annotation.annotation_type
    assert result.dataset_id == annotation.dataset_id
    assert result.parent_sample_id == annotation.parent_sample_id
    assert result.semantic_segmentation_details is None
    assert result.instance_segmentation_details is None
    assert result.object_detection_details is None


def test_create_annotation_failure(
    db_session: Session,
    dataset_id: UUID,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    mocker: MockerFixture,
) -> None:
    """Test create_annotation raises ValueError when creation fails."""
    # Mock the annotation_resolver.get_by_id to return None for failure simulation
    mock_get_by_id = mocker.patch("lightly_studio.resolvers.annotation_resolver.get_by_id")
    mock_get_by_id.return_value = None

    # Test that ValueError is raised
    with pytest.raises(ValueError, match="Failed to create annotation"):
        create_annotation(
            session=db_session,
            annotation=AnnotationCreateParams(
                annotation_label_id=annotation_labels[0].annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                dataset_id=dataset_id,
                parent_sample_id=samples[0].sample_id,
            ),
        )
