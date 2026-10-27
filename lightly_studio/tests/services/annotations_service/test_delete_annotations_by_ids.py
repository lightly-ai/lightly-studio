from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import evaluation_run_resolver
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_delete_annotations_by_ids__marks_evaluation_run_stale(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation_details = [
        AnnotationDetails(sample_id=image.sample_id, annotation_label_id=label.annotation_label_id)
    ]
    gt_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="ground_truth",
    )[0]
    pred_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="predictions",
    )[0]
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_annotation.annotation_collection_id,
            pred_annotation_collection_id=pred_annotation.annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    deleted_count = annotations_service.delete_annotations_by_ids(
        session=db_session, annotation_ids=[pred_annotation.sample_id]
    )

    assert deleted_count == 1
    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None
