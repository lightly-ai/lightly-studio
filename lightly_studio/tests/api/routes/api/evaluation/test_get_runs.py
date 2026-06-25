from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.collection import SampleType
from tests.api.routes.api.evaluation import helpers
from tests.helpers_resolvers import create_collection


def test_get_evaluation_runs(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    collection_ids = {
        name: create_collection(
            session=db_session,
            collection_name=name,
            sample_type=SampleType.ANNOTATION,
        ).collection_id
        for name in ("gt_v1", "pred_v1", "gt_v2", "pred_v2")
    }
    gt_1_id = collection_ids["gt_v1"]
    pred_1_id = collection_ids["pred_v1"]
    gt_2_id = collection_ids["gt_v2"]
    pred_2_id = collection_ids["pred_v2"]

    run_1_id = uuid4()
    run_2_id = uuid4()
    run_1_created_at = datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc)
    run_2_created_at = datetime(2026, 5, 17, 9, 30, 0, tzinfo=timezone.utc)
    mock_runs = [
        helpers.make_evaluation_run(
            run_id=run_1_id,
            name="run_1",
            config_json={"iou_threshold": 0.5, "classwise": True},
            created_at=run_1_created_at,
            gt_annotation_collection_id=gt_1_id,
            pred_annotation_collection_id=pred_1_id,
        ),
        helpers.make_evaluation_run(
            run_id=run_2_id,
            name="run_2",
            config_json={},
            created_at=run_2_created_at,
            gt_annotation_collection_id=gt_2_id,
            pred_annotation_collection_id=pred_2_id,
        ),
    ]
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.get_runs.evaluation_run_resolver.get_all_by_dataset_id",
        return_value=mock_runs,
    )

    response = test_client.get(f"/api/datasets/{uuid4()}/evaluation/runs")

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
        "lightly_studio.api.routes.api.evaluation.get_runs.evaluation_run_resolver.get_all_by_dataset_id",
        return_value=[],
    )

    response = test_client.get(f"/api/datasets/{dataset_id}/evaluation/runs")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []
