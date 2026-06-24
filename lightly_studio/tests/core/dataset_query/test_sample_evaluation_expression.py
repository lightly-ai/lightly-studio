from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query import AND
from lightly_studio.core.dataset_query.boolean_expression import NOT
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.evaluation_metric_expression import EvaluationMetricField
from lightly_studio.core.dataset_query.sample_evaluation_expression import SampleEvaluationQuery
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_sample_evaluation_query__filters_matching_samples(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    collection_id = dataset.collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/a.jpg"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/b.jpg"
    )
    gt_collection = create_collection(
        session=db_session,
        parent_collection_id=collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        parent_collection_id=collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run1",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="score",
                value=0.2,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_b.sample_id,
                metric_name="score",
                value=0.9,
            ),
        ],
    )

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(SampleEvaluationQuery("run1", EvaluationMetricField("score") > 0.5))
        .to_list()
    )

    assert [result.sample_id for result in results] == [image_b.sample_id]


def test_sample_evaluation_query__scopes_run_name_to_dataset(db_session: Session) -> None:
    """Test filtering when another dataset has a run with the same name."""
    dataset = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/a.jpg",
    )
    image_b = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/b.jpg",
    )
    gt_collection = create_collection(
        session=db_session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run1",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    other_dataset = create_collection(session=db_session)
    other_image = create_image(
        session=db_session,
        collection_id=other_dataset.collection_id,
        file_path_abs="/path/to/other.jpg",
    )
    other_gt_collection = create_collection(
        session=db_session,
        parent_collection_id=other_dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    other_pred_collection = create_collection(
        session=db_session,
        parent_collection_id=other_dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    other_run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run1",
            gt_annotation_collection_id=other_gt_collection.collection_id,
            dataset_id=other_gt_collection.dataset_id,
            pred_annotation_collection_id=other_pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="score",
                value=0.9,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_b.sample_id,
                metric_name="score",
                value=0.1,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=other_run.id,
                sample_id=other_image.sample_id,
                metric_name="score",
                value=0.0,
            ),
        ],
    )

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(SampleEvaluationQuery("run1", EvaluationMetricField("score") < 0.5))
        .to_list()
    )
    assert [result.sample_id for result in results] == [image_b.sample_id]

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(SampleEvaluationQuery("run1", NOT(EvaluationMetricField("score") > 0.5)))
        .to_list()
    )
    assert [result.sample_id for result in results] == [image_b.sample_id]


def test_sample_evaluation_query__matches_multiple_metrics(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/a.jpg",
    )
    image_b = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/b.jpg",
    )
    gt_collection = create_collection(
        session=db_session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run1",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="precision",
                value=0.9,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="recall",
                value=0.3,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_b.sample_id,
                metric_name="precision",
                value=0.9,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_b.sample_id,
                metric_name="recall",
                value=0.8,
            ),
        ],
    )

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(
            SampleEvaluationQuery(
                "run1",
                EvaluationMetricField("precision") > 0.5,
                EvaluationMetricField("recall") > 0.5,
            )
        )
        .to_list()
    )
    assert [result.sample_id for result in results] == [image_b.sample_id]

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(
            SampleEvaluationQuery(
                "run1",
                AND(
                    EvaluationMetricField("precision") > 0.5, EvaluationMetricField("recall") > 0.5
                ),
            )
        )
        .to_list()
    )
    assert [result.sample_id for result in results] == [image_b.sample_id]


def test_sample_evaluation_query__matches_run_without_criteria(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/a.jpg",
    )
    create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/b.jpg",
    )
    gt_collection = create_collection(
        session=db_session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run1",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="score",
                value=0.2,
            ),
        ],
    )

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(SampleEvaluationQuery(run_name="run1"))
        .to_list()
    )

    assert [result.sample_id for result in results] == [image_a.sample_id]
