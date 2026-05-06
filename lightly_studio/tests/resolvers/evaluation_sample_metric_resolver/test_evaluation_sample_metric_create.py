from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import evaluation_run_resolver, evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_create_many(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run, _ = _create_run_and_image(db_session, dataset_collection_id=dataset.collection_id)
    image1 = create_image(session=db_session, collection_id=dataset.collection_id)
    image2 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricTable(
                evaluation_run_id=run.id,
                sample_id=image1.sample_id,
                metric_name="ap",
                value=0.75,
            ),
            EvaluationSampleMetricTable(
                evaluation_run_id=run.id,
                sample_id=image2.sample_id,
                metric_name="ap",
                value=0.60,
            ),
        ],
    )

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert len(results) == 2
    sample_ids = {r.sample_id for r in results}
    assert sample_ids == {image1.sample_id, image2.sample_id}


def test_create_many__empty_list_is_noop(db_session: Session) -> None:
    run, _ = _create_run_and_image(db_session)

    evaluation_sample_metric_resolver.create_many(session=db_session, records=[])

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert results == []


def _create_run_and_image(
    session: Session,
    dataset_collection_id: UUID | None = None,
) -> tuple[EvaluationRunTable, ImageTable]:
    collection_id: UUID = (
        create_collection(session=session).collection_id
        if dataset_collection_id is None
        else dataset_collection_id
    )
    gt_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection_id,
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection_id,
    )
    run = evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name="test_run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    image = create_image(session=session, collection_id=collection_id)
    return run, image
