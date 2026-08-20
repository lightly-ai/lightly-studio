from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationTaskType,
)
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import create_collection


def test_marks_runs_matching_gt_collection(db_session: Session) -> None:
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
            name="run_gt",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=gt_collection.collection_id
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_marks_runs_matching_pred_collection(db_session: Session) -> None:
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
            name="run_pred",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=pred_collection.collection_id
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_does_not_mark_unrelated_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    target_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    other_gt = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    other_pred = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    # Run referencing target_collection as GT.
    run_matching = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_match",
            gt_annotation_collection_id=target_collection.collection_id,
            pred_annotation_collection_id=other_pred.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    # Unrelated run.
    run_unrelated = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_unrelated",
            gt_annotation_collection_id=other_gt.collection_id,
            pred_annotation_collection_id=other_pred.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.CLASSIFICATION,
        ),
    )

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=target_collection.collection_id
    )

    assert (
        evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_matching.id)
    ).stale_since is not None
    assert (
        evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_unrelated.id)
    ).stale_since is None


def test_marks_both_gt_and_pred_matches(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    shared_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    other_collection_a = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    other_collection_b = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    other_collection_c = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset.collection_id,
    )
    # Run with shared_collection as GT.
    run_gt = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_as_gt",
            gt_annotation_collection_id=shared_collection.collection_id,
            pred_annotation_collection_id=other_collection_a.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    # Run with shared_collection as pred.
    run_pred = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_as_pred",
            gt_annotation_collection_id=other_collection_b.collection_id,
            pred_annotation_collection_id=shared_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    # Unrelated run.
    run_unrelated = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_none",
            gt_annotation_collection_id=other_collection_b.collection_id,
            pred_annotation_collection_id=other_collection_c.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.CLASSIFICATION,
        ),
    )

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=shared_collection.collection_id
    )

    assert (
        evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_gt.id)
    ).stale_since is not None
    assert (
        evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_pred.id)
    ).stale_since is not None
    assert (
        evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run_unrelated.id)
    ).stale_since is None


def test_calling_twice_updates_stale_since(db_session: Session) -> None:
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
            name="run_twice",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=gt_collection.collection_id
    )
    first_stale_since = evaluation_run_resolver.get_by_id(
        session=db_session, evaluation_id=run.id
    ).stale_since

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=db_session, collection_id=gt_collection.collection_id
    )
    second_stale_since = evaluation_run_resolver.get_by_id(
        session=db_session, evaluation_id=run.id
    ).stale_since

    assert first_stale_since is not None
    assert second_stale_since is not None
    assert second_stale_since >= first_stale_since


def test_stale_since_defaults_to_none(db_session: Session) -> None:
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
