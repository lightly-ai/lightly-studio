"""Tests for update_annotation service method."""

from __future__ import annotations

from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
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
from tests.services.object_track_service import helpers as track_helpers


def test_update_annotation__calls_update_annotation_label(
    mocker: MockerFixture,
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
    mock_update_annotation_label = mocker.patch(
        "lightly_studio.services.annotations_service.update_annotation_label"
    )
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
    mocker: MockerFixture,
    db_session: Session,
    collection_id: UUID,
) -> None:
    annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    mock_update_temporal_span = mocker.patch(
        "lightly_studio.services.annotations_service.update_temporal_span"
    )
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


def test_update_annotation__polygons(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.POLYGON,
        polygons=[[(0, 0), (2, 0), (2, 2)]],
    )

    result = annotations_service.update_annotation(
        session=db_session,
        annotation_update=AnnotationUpdate(
            annotation_id=annotation.sample_id,
            collection_id=collection.collection_id,
            polygons=[[(0, 0), (9, 0), (9, 7)]],
        ),
    )

    assert result.polygon_details is not None
    assert result.polygon_details.polygons == [[[0, 0], [9, 0], [9, 7]]]
    assert (result.polygon_details.width, result.polygon_details.height) == (9, 7)


def test_update_annotation__cuboid_3d_interpolates_track_around_cuboid(
    db_session: Session,
) -> None:
    scene = track_helpers.create_scene(session=db_session)
    ticks = track_helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = track_helpers.create_track(session=db_session, scene=scene, number=1)
    track_helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, px=0.0)
    track_helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[1], track=track, px=0.0, interpolated=True
    )
    end_id = track_helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[2], track=track, px=0.0
    )
    end = annotation_resolver.get_by_id(session=db_session, annotation_id=end_id)
    assert end is not None
    assert end.cuboid_3d_details is not None

    annotations_service.update_annotation(
        session=db_session,
        annotation_update=AnnotationUpdate(
            annotation_id=end_id,
            collection_id=end.annotation_collection_id,
            cuboid_3d=Cuboid3DCreate.model_validate(
                end.cuboid_3d_details.model_dump() | {"px": 10.0}
            ),
        ),
    )

    by_tick = track_helpers.cuboids_by_tick(session=db_session, track=track)
    assert track_helpers.px_of(by_tick[ticks[1]][0]) == pytest.approx(5.0)
