"""Tests for the create-run route.

The route is thin: it validates the collection (404) and delegates to
``evaluation_service.run_evaluation``. The orchestration itself is covered by
the service tests, so here we only assert delegation, result propagation, and
the 404 the route owns.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_CREATED, HTTP_STATUS_NOT_FOUND
from lightly_studio.evaluation.image_dataset_evaluate import (
    EvaluationResult,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.evaluation_run import EvaluationTaskType
from tests.api.routes.api.evaluation import helpers

_RUN_EVALUATION = (
    "lightly_studio.api.routes.api.evaluation.create_run.evaluation_service.run_evaluation"
)


def test_create_evaluation_run__delegates_to_service_and_propagates_result(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    run_id = uuid4()
    run_evaluation = mocker.patch(
        _RUN_EVALUATION,
        return_value=EvaluationResult(
            evaluation_run_id=run_id,
            sample_count=2,
            gt_annotation_count=2,
            pred_annotation_count=2,
        ),
    )

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(root.collection_id),
            "name": "run-1",
            "config": {"iou_threshold": 0.7, "classwise": False},
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json() == {
        "evaluation_run_id": str(run_id),
        "sample_count": 2,
        "gt_annotation_count": 2,
        "pred_annotation_count": 2,
    }

    run_evaluation.assert_called_once()
    kwargs = run_evaluation.call_args.kwargs
    assert kwargs["collection"].collection_id == root.collection_id
    assert kwargs["task_type"] == EvaluationTaskType.OBJECT_DETECTION
    assert kwargs["gt_annotation_source"] == "gt"
    assert kwargs["pred_annotation_source"] == "pred"
    assert kwargs["name"] == "run-1"
    assert kwargs["filters"] is None
    assert isinstance(kwargs["config"], ObjectDetectionEvaluationConfig)
    assert kwargs["config"].iou_threshold == 0.7
    assert kwargs["config"].classwise is False


def test_create_evaluation_run__collection_not_found_returns_404(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    run_evaluation = mocker.patch(_RUN_EVALUATION)

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(uuid4()),
        },
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    run_evaluation.assert_not_called()
