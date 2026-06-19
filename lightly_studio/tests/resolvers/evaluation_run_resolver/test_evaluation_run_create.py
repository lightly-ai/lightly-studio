from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import create_collection


def test_create_evaluation_run(db_session: Session) -> None:
    root = create_collection(session=db_session)
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=root.collection_id,
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=root.collection_id,
    )

    evaluation_run_input = EvaluationRunCreate(
        name="test_evaluation_run",
        gt_annotation_collection_id=gt_collection.collection_id,
        dataset_id=gt_collection.dataset_id,
        pred_annotation_collection_id=pred_collection.collection_id,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        config_json={"iou_threshold": 0.5},
    )

    evaluation_run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=evaluation_run_input,
    )

    assert isinstance(evaluation_run, EvaluationRunTable)
    assert evaluation_run.name == "test_evaluation_run"
    assert evaluation_run.gt_annotation_collection_id == gt_collection.collection_id
    assert evaluation_run.pred_annotation_collection_id == pred_collection.collection_id
    assert evaluation_run.task_type == EvaluationTaskType.OBJECT_DETECTION
    assert evaluation_run.config_json == {"iou_threshold": 0.5}
    assert evaluation_run.id is not None
    assert evaluation_run.created_at is not None


def test_create_evaluation_run__duplicate_name_same_dataset(db_session: Session) -> None:
    root = create_collection(session=db_session)
    gt_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=root.collection_id,
    )
    pred_collection = create_collection(
        session=db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=root.collection_id,
    )

    evaluation_run_input = EvaluationRunCreate(
        name="duplicate_run",
        gt_annotation_collection_id=gt_collection.collection_id,
        dataset_id=gt_collection.dataset_id,
        pred_annotation_collection_id=pred_collection.collection_id,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
    )

    # Create the first evaluation run
    evaluation_run_resolver.create(session=db_session, evaluation_run_input=evaluation_run_input)
    db_session.commit()

    # Try to create second with the same name and dataset
    def create_duplicate() -> None:
        evaluation_run_resolver.create(
            session=db_session, evaluation_run_input=evaluation_run_input
        )
        db_session.commit()

    with pytest.raises(IntegrityError):
        create_duplicate()
    db_session.rollback()
