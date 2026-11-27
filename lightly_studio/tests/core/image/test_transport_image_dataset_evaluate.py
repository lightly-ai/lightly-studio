from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import select

from lightly_studio.core.dataset_query import ImageSampleField, OrderByField
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.image.transport_image_dataset_evaluate import TransportImageDatasetEvaluate
from lightly_studio.database import db_manager
from lightly_studio.evaluation.image_dataset_evaluate import ImageDatasetEvaluate
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.evaluation_task import (
    ClassificationEvaluationConfig,
    EvaluationConfig,
    EvaluationTask,
    InstanceSegmentationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from lightly_studio.transport import active_transport
from lightly_studio.transport.local.local_compute_transport import LocalComputeTransport
from tests.api.routes.api.evaluation import helpers as evaluation_helpers

RUN_ID = uuid4()


@pytest.mark.usefixtures("patch_collection")
class TestTransportImageDatasetEvaluate:
    def test_object_detection(self, mocker: MockerFixture) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        query = dataset.match(ImageSampleField.width > 10)
        transport = mocker.patch.object(active_transport, "get_transport").return_value
        evaluate = TransportImageDatasetEvaluate(
            session=dataset.session, collection_id=dataset.collection_id, query=query
        )

        result = evaluate.object_detection(
            name="run",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
            config=ObjectDetectionEvaluationConfig(iou_threshold=0.7),
        )

        transport.compute.evaluate.assert_called_once_with(
            collection_id=dataset.collection_id,
            request=SampleQueryRequest(
                query_expr=QueryExpr(
                    match_expr=IntegerExpr(
                        field=FieldRef(table="image", name="width"),
                        operator=OrdinalComparisonOperator.GT,
                        value=10,
                    )
                )
            ),
            limit=None,
            task=EvaluationTask(
                task_type=EvaluationTaskType.OBJECT_DETECTION,
                name="run",
                gt_annotation_source="gt",
                pred_annotation_source="pred",
                config=ObjectDetectionEvaluationConfig(iou_threshold=0.7),
            ),
        )
        assert result == transport.compute.evaluate.return_value
        assert "sample_ids" not in vars(evaluate)

    def test_object_detection__ordered_and_sliced_query(self, mocker: MockerFixture) -> None:
        session = db_manager.persistent_session()
        collection = evaluation_helpers.create_dataset_with_annotations(
            db_session=session, image_widths=(30, 10, 20, 40)
        )
        query = DatasetQuery(dataset=collection).order_by(OrderByField(ImageSampleField.width))[1:3]
        sql_sample_ids = {sample.sample_id for sample in query}
        transport_evaluate = mocker.spy(LocalComputeTransport, "evaluate")

        result = TransportImageDatasetEvaluate(
            session=session, collection_id=collection.collection_id, query=query
        ).object_detection(name="run", gt_annotation_source="gt", pred_annotation_source="pred")

        metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
            session=session, evaluation_run_id=result.evaluation_run_id
        )
        assert {metric.sample_id for metric in metrics} == sql_sample_ids
        assert {sample.width for sample in query} == {20, 30}
        transport_evaluate.assert_called_once()

    @pytest.mark.parametrize(
        ("method_name", "default_config"),
        [
            ("object_detection", ObjectDetectionEvaluationConfig()),
            ("classification", ClassificationEvaluationConfig()),
            ("semantic_segmentation", SemanticSegmentationEvaluationConfig()),
            ("instance_segmentation", InstanceSegmentationEvaluationConfig()),
        ],
    )
    @pytest.mark.parametrize(
        "make_query",
        [
            lambda dataset: dataset.query().filter_by_sample_ids(select(SampleTable.sample_id)),
            lambda dataset: DatasetQuery(dataset=dataset._inner, session=dataset.session),
        ],
    )
    def test_evaluate__unsupported_query_or_query_with_session(
        self,
        mocker: MockerFixture,
        make_query: Callable[[ImageDataset], DatasetQuery],
        method_name: str,
        default_config: EvaluationConfig,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        evaluate_locally = mocker.patch.object(ImageDatasetEvaluate, method_name)
        transport_evaluate = mocker.spy(LocalComputeTransport, "evaluate")
        evaluate = TransportImageDatasetEvaluate(
            session=dataset.session, collection_id=dataset.collection_id, query=make_query(dataset)
        )

        result = getattr(evaluate, method_name)(
            name="run", gt_annotation_source="gt", pred_annotation_source="pred"
        )

        evaluate_locally.assert_called_once_with(
            name="run",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
            config=default_config,
        )
        assert result == evaluate_locally.return_value
        transport_evaluate.assert_not_called()

    @pytest.mark.parametrize(
        ("read", "transport_method", "run_kwargs"),
        [
            (lambda evaluate: evaluate.list_runs(), "list_evaluation_runs", {}),
            (
                lambda evaluate: evaluate.confusion_matrix(run_id=RUN_ID),
                "get_evaluation_confusion_matrix",
                {"run_id": RUN_ID},
            ),
            (
                lambda evaluate: evaluate.metrics(run_id=RUN_ID),
                "get_evaluation_metrics",
                {"run_id": RUN_ID},
            ),
        ],
    )
    def test_read_methods(
        self,
        mocker: MockerFixture,
        read: Callable[[TransportImageDatasetEvaluate], object],
        transport_method: str,
        run_kwargs: dict[str, UUID],
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        transport = mocker.patch.object(active_transport, "get_transport").return_value
        evaluate = TransportImageDatasetEvaluate(
            session=dataset.session, collection_id=dataset.collection_id, query=dataset.query()
        )

        result = read(evaluate)

        transport_read = getattr(transport.compute, transport_method)
        transport_read.assert_called_once_with(collection_id=dataset.collection_id, **run_kwargs)
        assert result == transport_read.return_value
