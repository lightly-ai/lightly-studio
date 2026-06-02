from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_NOT_IMPLEMENTED,
    HTTP_STATUS_OK,
)
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    ConfusionMatrix,
)
from lightly_studio.models.evaluation_run import (
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import (
    EvaluationRunMetricsInfoView,
    EvaluationSampleMetricBoundsView,
)


def _make_evaluation_run(  # noqa: PLR0913
    *,
    run_id: UUID,
    name: str,
    config_json: dict[str, Any],
    created_at: datetime,
    gt_annotation_collection_id: UUID | None = None,
    pred_annotation_collection_id: UUID | None = None,
    task_type: EvaluationTaskType = EvaluationTaskType.OBJECT_DETECTION,
) -> EvaluationRunTable:
    return EvaluationRunTable(
        id=run_id,
        name=name,
        gt_annotation_collection_id=gt_annotation_collection_id or uuid4(),
        pred_annotation_collection_id=pred_annotation_collection_id or uuid4(),
        task_type=task_type,
        config_json=config_json,
        created_at=created_at,
    )


def _insert_collection(session: Session, dataset_id: UUID, name: str) -> UUID:
    collection = CollectionTable(
        name=name,
        dataset_id=dataset_id,
        sample_type=SampleType.ANNOTATION,
    )
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection.collection_id


def test_get_evaluation_sample_metrics_info(test_client: TestClient, mocker: MockerFixture) -> None:
    dataset_id = uuid4()
    mock_result = [
        EvaluationRunMetricsInfoView(
            run_name="run_1",
            metrics=[
                EvaluationSampleMetricBoundsView(
                    metric_name="precision", min_value=0.6, max_value=0.9
                ),
                EvaluationSampleMetricBoundsView(
                    metric_name="recall", min_value=0.7, max_value=0.8
                ),
            ],
        ),
        EvaluationRunMetricsInfoView(
            run_name="run_2",
            metrics=[
                EvaluationSampleMetricBoundsView(metric_name="ap", min_value=0.5, max_value=0.5),
            ],
        ),
    ]
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id",
        return_value=mock_result,
    )

    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/metrics/sample/info")

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["run_name"] == "run_1"
    assert len(data[0]["metrics"]) == 2
    run1_bounds = {m["metric_name"]: m for m in data[0]["metrics"]}
    assert run1_bounds["precision"]["min_value"] == 0.6
    assert run1_bounds["precision"]["max_value"] == 0.9
    assert run1_bounds["recall"]["min_value"] == 0.7
    assert run1_bounds["recall"]["max_value"] == 0.8
    assert data[1]["run_name"] == "run_2"
    assert len(data[1]["metrics"]) == 1
    assert data[1]["metrics"][0]["metric_name"] == "ap"
    assert data[1]["metrics"][0]["min_value"] == 0.5
    assert data[1]["metrics"][0]["max_value"] == 0.5


def test_get_evaluation_sample_metrics_info__empty_response(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id",
        return_value=[],
    )

    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/metrics/sample/info")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_evaluation_runs(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    dataset = DatasetTable()
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    gt_1_id = _insert_collection(db_session, dataset.dataset_id, "gt_v1")
    pred_1_id = _insert_collection(db_session, dataset.dataset_id, "pred_v1")
    gt_2_id = _insert_collection(db_session, dataset.dataset_id, "gt_v2")
    pred_2_id = _insert_collection(db_session, dataset.dataset_id, "pred_v2")

    run_1_id = uuid4()
    run_2_id = uuid4()
    run_1_created_at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc)
    run_2_created_at = datetime(2026, 5, 17, 9, 30, 0, tzinfo=timezone.utc)
    mock_runs = [
        _make_evaluation_run(
            run_id=run_1_id,
            name="run_1",
            config_json={"iou_threshold": 0.5, "classwise": True},
            created_at=run_1_created_at,
            gt_annotation_collection_id=gt_1_id,
            pred_annotation_collection_id=pred_1_id,
        ),
        _make_evaluation_run(
            run_id=run_2_id,
            name="run_2",
            config_json={},
            created_at=run_2_created_at,
            gt_annotation_collection_id=gt_2_id,
            pred_annotation_collection_id=pred_2_id,
        ),
    ]
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_all_by_dataset_id",
        return_value=mock_runs,
    )

    response = test_client.get(f"/api/datasets/{dataset.dataset_id}/evaluation/runs")

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data == [
        {
            "id": str(run_1_id),
            "name": "run_1",
            "evaluation_run_configuration": {"iou_threshold": 0.5, "classwise": True},
            "created_at": "2026-05-18T10:00:00Z",
            "gt_annotation_source": "gt_v1",
            "pred_annotation_source": "pred_v1",
        },
        {
            "id": str(run_2_id),
            "name": "run_2",
            "evaluation_run_configuration": {},
            "created_at": "2026-05-17T09:30:00Z",
            "gt_annotation_source": "gt_v2",
            "pred_annotation_source": "pred_v2",
        },
    ]


def test_get_evaluation_runs__empty_response(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_all_by_dataset_id",
        return_value=[],
    )

    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/runs")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_evaluation_confusion_matrix(test_client: TestClient, mocker: MockerFixture) -> None:
    dataset_id = uuid4()
    evaluation_run_id = uuid4()
    mock_matrix = ConfusionMatrix(
        row_labels=["cat", NO_GROUND_TRUTH_ROW_LABEL],
        col_labels=["cat", NO_PREDICTION_COL_LABEL],
        counts=[[2, 0], [0, 1]],
    )
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_by_id",
        return_value=_make_evaluation_run(
            run_id=evaluation_run_id,
            name="run_1",
            config_json={},
            created_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
        ),
    )
    mock_resolver = mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix",
        return_value=mock_matrix,
    )

    response = test_client.get(
        f"/api/datasets/{dataset_id}/evaluation/runs/{evaluation_run_id}/confusion-matrix"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "row_labels": ["cat", NO_GROUND_TRUTH_ROW_LABEL],
        "col_labels": ["cat", NO_PREDICTION_COL_LABEL],
        "counts": [[2, 0], [0, 1]],
    }
    mock_resolver.assert_called_once_with(
        session=mocker.ANY,
        evaluation_run_id=evaluation_run_id,
    )


def test_get_evaluation_confusion_matrix__empty_matrix(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    evaluation_run_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_by_id",
        return_value=_make_evaluation_run(
            run_id=evaluation_run_id,
            name="run_1",
            config_json={},
            created_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
        ),
    )
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix",
        return_value=ConfusionMatrix(
            row_labels=[],
            col_labels=[],
            counts=[],
        ),
    )

    response = test_client.get(
        f"/api/datasets/{dataset_id}/evaluation/runs/{evaluation_run_id}/confusion-matrix"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"row_labels": [], "col_labels": [], "counts": []}


def test_get_evaluation_confusion_matrix__run_not_found(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    evaluation_run_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_by_id",
        return_value=None,
    )

    response = test_client.get(
        f"/api/datasets/{dataset_id}/evaluation/runs/{evaluation_run_id}/confusion-matrix"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_evaluation_confusion_matrix__unsupported_task_type(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    evaluation_run_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_by_id",
        return_value=_make_evaluation_run(
            run_id=evaluation_run_id,
            name="run_1",
            config_json={},
            created_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
            task_type=EvaluationTaskType.CLASSIFICATION,
        ),
    )
    mock_resolver = mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_annotation_metric_resolver.get_object_detection_confusion_matrix",
    )

    response = test_client.get(
        f"/api/datasets/{dataset_id}/evaluation/runs/{evaluation_run_id}/confusion-matrix"
    )

    assert response.status_code == HTTP_STATUS_NOT_IMPLEMENTED
    assert response.json() == {
        "detail": "Evaluation task type 'classification' is not supported yet.",
    }
    mock_resolver.assert_not_called()
