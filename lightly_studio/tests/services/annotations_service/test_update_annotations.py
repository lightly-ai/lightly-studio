"""Tests for update_annotations service method."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
    object_track_resolver,
)
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_update_annotations__updates_label_for_all_track_annotations(
    db_session: Session,
) -> None:
    """Updating one annotation label updates all track siblings."""
    collection = create_collection(session=db_session)
    root_collection_id = collection.collection_id

    label_before = create_annotation_label(
        session=db_session, root_collection_id=root_collection_id, label_name="a"
    )
    label_after = create_annotation_label(
        session=db_session, root_collection_id=root_collection_id, label_name="b"
    )

    img_1 = create_image(
        session=db_session, collection_id=root_collection_id, file_path_abs="/tmp/1.png"
    )
    img_2 = create_image(
        session=db_session, collection_id=root_collection_id, file_path_abs="/tmp/2.png"
    )
    img_3 = create_image(
        session=db_session, collection_id=root_collection_id, file_path_abs="/tmp/3.png"
    )

    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )
    assert len(track_ids) == 2
    track_a, track_b = track_ids
    annotations = create_annotations(
        session=db_session,
        collection_id=root_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=img_1.sample_id,
                annotation_label_id=label_before.annotation_label_id,
                object_track_id=track_a,
            ),
            AnnotationDetails(
                sample_id=img_2.sample_id,
                annotation_label_id=label_before.annotation_label_id,
                object_track_id=track_a,
            ),
            AnnotationDetails(
                sample_id=img_3.sample_id,
                annotation_label_id=label_before.annotation_label_id,
                object_track_id=track_b,
            ),
        ],
    )
    track_a_annotations = [
        annotation for annotation in annotations if annotation.object_track_id == track_a
    ]
    track_b_annotations = [
        annotation for annotation in annotations if annotation.object_track_id == track_b
    ]
    assert len(track_a_annotations) == 2
    updated = annotations_service.update_annotations(
        session=db_session,
        annotation_updates=[
            AnnotationUpdate(
                annotation_id=track_a_annotations[0].sample_id,
                collection_id=root_collection_id,
                label_name=label_after.annotation_label_name,
            )
        ],
    )

    assert len(updated) == 1
    assert updated[0].sample_id == track_a_annotations[0].sample_id
    assert updated[0].annotation_label_id == label_after.annotation_label_id

    sibling_after_update = annotation_resolver.get_by_id(
        db_session, track_a_annotations[1].sample_id
    )
    assert sibling_after_update is not None
    assert sibling_after_update.annotation_label_id == label_after.annotation_label_id

    outside_after = annotation_resolver.get_by_id(db_session, track_b_annotations[0].sample_id)
    assert outside_after is not None
    assert outside_after.annotation_label_id == label_before.annotation_label_id


def test_update_annotations_marks_evaluation_run_stale(db_session: Session) -> None:
    image_collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=image_collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=image_collection.collection_id,
        label_name="cat",
    )
    pred_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="pred",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=image_collection.collection_id,
        ),
    )
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=image_collection.collection_id,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=image_collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
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

    annotations_service.update_annotations(
        session=db_session,
        annotation_updates=[
            AnnotationUpdate(
                annotation_id=annotation.sample_id,
                collection_id=pred_collection.collection_id,
                label_name="dog",
            ),
        ],
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
