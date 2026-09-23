"""Tests for update_annotation service method."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import (
    AnnotationUpdate,
)
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_annotation__calls_update_annotation_label(
    db_session: Session,
    collection_id: UUID,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test updating annotation."""
    # Get all annotations and pick the first one
    annotations = annotation_resolver.get_all(db_session)
    first_annotation = annotations.annotations[0]
    annotation_id = first_annotation.sample_id

    # Get a different existing label
    target_label = annotations_test_data.annotation_labels[1]
    target_label_name = target_label.annotation_label_name

    # Spy on the update_annotation_label function call
    with patch(
        "lightly_studio.services.annotations_service.update_annotation_label"
    ) as mock_update_annotation_label:
        # Update the annotation label using the service
        updated_annotation = annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                label_name=target_label_name,
                collection_id=collection_id,
            ),
        )

        # Verify the spy was called with correct arguments
        mock_update_annotation_label.assert_called_once_with(
            session=db_session,
            annotation_id=annotation_id,
            label_name=target_label_name,
        )

    assert updated_annotation is not None


def test_update_annotation__raises_error_when_label_name_is_none(
    db_session: Session,
    collection_id: UUID,
) -> None:
    """Test that update_annotation raises ValueError when label_name is None."""
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    with pytest.raises(ValueError, match="No updates provided for the annotation"):
        annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                label_name=None,
                collection_id=collection_id,
            ),
        )


def test_update_annotation__raises_error_when_only_start_time_s_is_provided(
    db_session: Session,
    collection_id: UUID,
) -> None:
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    with pytest.raises(
        ValueError, match="Both start_time_s and end_time_s must be provided together"
    ):
        annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                collection_id=collection_id,
                start_time_s=1.0,
            ),
        )


def test_update_annotation__raises_error_when_only_end_time_s_is_provided(
    db_session: Session,
    collection_id: UUID,
) -> None:
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    with pytest.raises(
        ValueError, match="Both start_time_s and end_time_s must be provided together"
    ):
        annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                collection_id=collection_id,
                end_time_s=5.0,
            ),
        )


def test_update_annotation__calls_update_temporal_span_when_both_times_provided(
    db_session: Session,
    collection_id: UUID,
) -> None:
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    with patch(
        "lightly_studio.services.annotations_service.update_temporal_span"
    ) as mock_update_temporal_span:
        annotations_service.update_annotation(
            db_session,
            AnnotationUpdate(
                annotation_id=annotation_id,
                collection_id=collection_id,
                start_time_s=1.0,
                end_time_s=5.0,
            ),
        )

        mock_update_temporal_span.assert_called_once_with(
            session=db_session,
            annotation_id=annotation_id,
            start_time_s=1.0,
            end_time_s=5.0,
        )


def test_update_annotation__marks_evaluation_run_stale(db_session: Session) -> None:
    image_collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=image_collection.collection_id,
        label_name="cat",
    )
    gt_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="gt",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=image_collection.collection_id,
        ),
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=image_collection.collection_id,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=image_collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    annotations_service.update_annotation(
        session=db_session,
        annotation_update=AnnotationUpdate(
            annotation_id=annotation.sample_id,
            collection_id=gt_collection.collection_id,
            label_name="dog",
        ),
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
