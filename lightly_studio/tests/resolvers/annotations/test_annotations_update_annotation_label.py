"""Tests for updating annotation labels."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio import AnnotationType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)
from tests.conftest import AnnotationsTestData, assert_contains_properties
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    get_annotation_by_type,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_update_annotation_label_classification(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating a classification label preserves its temporal span."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    first_annotation = annotations[0]
    annotation_id = first_annotation.sample_id
    current_annotation_label_id = first_annotation.annotation_label_id
    new_label = annotations_test_data.annotation_labels[1]

    assert current_annotation_label_id != new_label.annotation_label_id

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_label.annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None
    assert (
        updated_annotation.annotation_label.annotation_label_name == new_label.annotation_label_name
    )

    # Verify the temporal span was preserved across the update.
    assert updated_annotation.temporal_span_details is not None
    assert updated_annotation.temporal_span_details.start_time_s == 1.5
    assert updated_annotation.temporal_span_details.end_time_s == 4.0


def test_update_annotation_with_tags(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
    annotation_tags_assigned: list[TagTable],  # noqa: ARG001
) -> None:
    """Test updating annotation labels."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = annotations[0]
    annotation_id = annotation.sample_id
    current_annotation_label_id = annotation.annotation_label_id
    new_label = annotations_test_data.annotation_labels[1]
    existing_tags = [tag.tag_id for tag in annotation.sample.tags]

    assert current_annotation_label_id != new_label.annotation_label_id

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_label.annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None

    tags = [tag.tag_id for tag in updated_annotation.sample.tags]
    assert tags == existing_tags


def test_update_annotation_label_object_detection(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating object detection annotation label."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = get_annotation_by_type(
        annotations=annotations, annotation_type=AnnotationType.OBJECT_DETECTION
    )

    current_annotation_label_id = annotation.annotation_label_id
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    assert annotation.object_detection_details

    x = annotation.object_detection_details.x
    y = annotation.object_detection_details.y
    width = annotation.object_detection_details.width
    height = annotation.object_detection_details.height

    assert annotation.object_detection_details is not None
    assert current_annotation_label_id != new_annotation_label_id

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation.sample_id,
        new_annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation.sample_id)

    assert updated_annotation is not None
    assert updated_annotation.annotation_label_id == new_annotation_label_id

    assert_contains_properties(
        updated_annotation.object_detection_details,
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
    )


def test_update_annotation_label_segmentation_mask(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation labels."""
    annotations = annotation_resolver.get_all(
        db_session,
    ).annotations
    annotation = get_annotation_by_type(
        annotations=annotations, annotation_type=AnnotationType.SEGMENTATION_MASK
    )
    annotation_id = annotation.sample_id
    current_annotation_label_id = annotation.annotation_label_id
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    assert annotation.segmentation_details
    x = annotation.segmentation_details.x
    y = annotation.segmentation_details.y
    width = annotation.segmentation_details.width
    height = annotation.segmentation_details.height
    segmentation_mask = annotation.segmentation_details.segmentation_mask

    assert current_annotation_label_id != new_annotation_label_id
    assert annotation.segmentation_details is not None

    # Update the label of the first annotation
    annotation_resolver.update_annotation_label(
        db_session,
        annotation_id,
        new_annotation_label_id,
    )

    # Verify that the label has been updated
    updated_annotation = annotation_resolver.get_by_id(db_session, annotation_id)

    assert updated_annotation is not None
    assert updated_annotation.annotation_label_id == new_annotation_label_id
    assert_contains_properties(
        updated_annotation.segmentation_details,
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "segmentation_mask": segmentation_mask,
        },
    )


def test_update_annotation_label_raise_error_on_wrong_annotation_id(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test for wrong annotation_id."""
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")
    new_annotation_label_id = annotations_test_data.annotation_labels[1].annotation_label_id

    with pytest.raises(ValueError, match=f"Annotation with ID {annotation_id} not found."):
        annotation_resolver.update_annotation_label(
            db_session,
            annotation_id,
            new_annotation_label_id,
        )


def test_update_annotation_label__deletes_evaluation_metrics(
    db_session: Session,
) -> None:
    """Test label updates remove invalidated evaluation annotation and sample metrics."""
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    collection_id = dataset.collection_id
    old_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="old_label",
    )
    new_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="new_label",
    )
    pred_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=old_label.annotation_label_id,
    )
    gt_annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=old_label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                metric_name="iou",
                value=0.75,
            )
        ],
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                metric_name="score",
                value=0.5,
            )
        ],
    )

    annotation_resolver.update_annotation_label(
        session=db_session,
        annotation_id=gt_annotation.sample_id,
        annotation_label_id=new_label.annotation_label_id,
    )

    updated_annotation = annotation_resolver.get_by_id(
        session=db_session,
        annotation_id=gt_annotation.sample_id,
    )
    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert updated_annotation is not None
    assert updated_annotation.annotation_label_id == new_label.annotation_label_id
    assert annotation_metrics == []
    assert sample_metrics == []
