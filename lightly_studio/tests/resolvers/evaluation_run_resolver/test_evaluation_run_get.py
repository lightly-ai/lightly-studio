from __future__ import annotations

import uuid
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import create_collection


def test_get_by_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = _create_evaluation_run(db_session, dataset_collection_id=dataset.collection_id)

    result = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)

    assert isinstance(result, EvaluationRunTable)
    assert result.id == run.id
    assert result.name == run.name


def test_get_by_id__returns_none_for_unknown_id(db_session: Session) -> None:
    result = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=uuid.uuid4())

    assert result is None


def test_get_all_by_dataset_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run1 = _create_evaluation_run(
        db_session, dataset_collection_id=dataset.collection_id, name="run_1"
    )
    run2 = _create_evaluation_run(
        db_session, dataset_collection_id=dataset.collection_id, name="run_2"
    )

    results = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    )

    assert len(results) == 2
    assert all(isinstance(r, EvaluationRunTable) for r in results)
    # newest first
    assert results[0].id == run2.id
    assert results[1].id == run1.id


def test_get_all_by_dataset_id__returns_empty_for_unknown_dataset(db_session: Session) -> None:
    results = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=uuid.uuid4()
    )

    assert results == []


def test_get_all_by_dataset_id__excludes_other_datasets(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    other_dataset = create_collection(session=db_session)
    run = _create_evaluation_run(db_session, dataset_collection_id=dataset.collection_id)
    _create_evaluation_run(db_session, dataset_collection_id=other_dataset.collection_id)

    results = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    )

    assert len(results) == 1
    assert results[0].id == run.id


def _create_evaluation_run(
    session: Session,
    dataset_collection_id: UUID,
    name: str = "test_run",
) -> EvaluationRunTable:
    gt_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset_collection_id,
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset_collection_id,
    )
    return evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name=name,
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
