from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.evaluation_sample_metric import (
    EvaluationRunMetricsInfoView,
    EvaluationSampleMetricBoundsView,
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
