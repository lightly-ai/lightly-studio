from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.image.transport_image_dataset_evaluate import TransportImageDatasetEvaluate
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
from lightly_studio.transport import active_transport
from lightly_studio.transport.local.local_compute_transport import LocalComputeTransport

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
            query_expr=QueryExpr(
                match_expr=IntegerExpr(
                    field=FieldRef(table="image", name="width"),
                    operator=OrdinalComparisonOperator.GT,
                    value=10,
                )
            ),
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
            lambda dataset: dataset.query()[:1],
            lambda dataset: DatasetQuery(dataset=dataset._inner, session=dataset.session),
        ],
    )
    def test_evaluate__sliced_query_or_query_with_session(
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
