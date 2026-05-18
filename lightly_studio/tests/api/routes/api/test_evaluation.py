from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.evaluation_run import (
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import (
    EvaluationRunMetricsInfoView,
    EvaluationSampleMetricBoundsView,
)


def _make_evaluation_run(
    *,
    run_id: UUID,
    name: str,
    config_json: dict[str, Any],
    created_at: datetime,
) -> EvaluationRunTable:
    return EvaluationRunTable(
        id=run_id,
        name=name,
        gt_annotation_collection_id=uuid4(),
        pred_annotation_collection_id=uuid4(),
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        config_json=config_json,
        created_at=created_at,
    )


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


def test_get_evaluation_runs(test_client: TestClient, mocker: MockerFixture) -> None:
    dataset_id = uuid4()
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
        ),
        _make_evaluation_run(
            run_id=run_2_id,
            name="run_2",
            config_json={},
            created_at=run_2_created_at,
        ),
    ]
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.evaluation_run_resolver.get_all_by_dataset_id",
        return_value=mock_runs,
    )

    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/runs")

    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data == [
        {
            "id": str(run_1_id),
            "name": "run_1",
            "evaluation_run_configuration": {"iou_threshold": 0.5, "classwise": True},
            "created_at": "2026-05-18T10:00:00Z",
        },
        {
            "id": str(run_2_id),
            "name": "run_2",
            "evaluation_run_configuration": {},
            "created_at": "2026-05-17T09:30:00Z",
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
