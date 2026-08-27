from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.evaluation_run import EvaluationRunView


def test_get_evaluation_runs(test_client: TestClient, mocker: MockerFixture) -> None:
    run_1_id = uuid4()
    run_2_id = uuid4()
    views = [
        EvaluationRunView(
            id=run_1_id,
            name="run_1",
            evaluation_run_configuration={"iou_threshold": 0.5, "classwise": True},
            created_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
            gt_annotation_source="gt_v1",
            pred_annotation_source="pred_v1",
        ),
        EvaluationRunView(
            id=run_2_id,
            name="run_2",
            evaluation_run_configuration={},
            created_at=datetime(2026, 5, 17, 9, 30, 0, tzinfo=timezone.utc),
            gt_annotation_source="gt_v2",
            pred_annotation_source="pred_v2",
        ),
    ]
    list_views = mocker.patch(
        "lightly_studio.api.routes.api.evaluation.get_runs.evaluation_run_resolver.list_views_by_dataset_id",
        return_value=views,
    )

    dataset_id = uuid4()
    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/runs")

    assert list_views.call_args.kwargs["dataset_id"] == dataset_id
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
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
        "lightly_studio.api.routes.api.evaluation.get_runs.evaluation_run_resolver.list_views_by_dataset_id",
        return_value=[],
    )

    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/runs")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []
