from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationTaskType,
)
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import create_collection


def test_clear_stale_since__stale_run(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_stale",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=gt_collection.collection_id
    )
    stale_run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert stale_run is not None
    assert stale_run.stale_since is not None

    evaluation_run_resolver.clear_stale_since(session=db_session, evaluation_run_id=run.id)

    cleared_run = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert cleared_run is not None
    assert cleared_run.stale_since is None


def test_clear_stale_since__non_stale_run_is_noop(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_fresh",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    evaluation_run_resolver.clear_stale_since(session=db_session, evaluation_run_id=run.id)

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is None


def test_clear_stale_since__does_not_affect_other_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    run_a = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_a",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    run_b = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_b",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=gt_collection.collection_id
    )

    evaluation_run_resolver.clear_stale_since(session=db_session, evaluation_run_id=run_a.id)

    run_a_refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_a.id)
    assert run_a_refreshed is not None
    assert run_a_refreshed.stale_since is None

    run_b_refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_b.id)
    assert run_b_refreshed is not None
    assert run_b_refreshed.stale_since is not None
