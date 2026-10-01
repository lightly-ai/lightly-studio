"""Tests for the recompute-run route.

The route is thin: it validates the run (404) and delegates to
``evaluation_service.recompute_evaluation_run``. Integration is covered by
the service tests; here we only assert delegation, result propagation, and
the 404 the route owns.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.evaluation.image_dataset_evaluate import (
    EvaluationResult,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.services import evaluation_service
from tests.api.routes.api.evaluation import helpers

_RECOMPUTE = (
    "lightly_studio.api.routes.api.evaluation.recompute_run"
    ".evaluation_service.recompute_evaluation_run"
)


def test_recompute_evaluation_run__delegates_to_service_and_propagates_result(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    run = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
        name="run-1",
    )
    run_id = run.evaluation_run_id

    recompute = mocker.patch(
        _RECOMPUTE,
        return_value=EvaluationResult(
            evaluation_run_id=run_id,
            sample_count=1,
            gt_annotation_count=1,
            pred_annotation_count=1,
        ),
    )

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/{run_id}/recompute"
    )

    assert response.status_code == 200
    assert response.json() == {
        "evaluation_run_id": str(run_id),
        "sample_count": 1,
        "gt_annotation_count": 1,
        "pred_annotation_count": 1,
    }
    recompute.assert_called_once()
    kwargs = recompute.call_args.kwargs
    assert kwargs["run"].id == run_id


def test_recompute_evaluation_run__run_not_found_returns_404(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    recompute = mocker.patch(_RECOMPUTE)

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/{uuid4()}/recompute"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    recompute.assert_not_called()


def test_recompute_evaluation_run__run_in_different_dataset_returns_404(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    other_root = helpers.create_dataset_with_annotations(db_session)
    run = evaluation_service.run_evaluation(
        session=db_session,
        collection=other_root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
        name="run-other",
    )
    recompute = mocker.patch(_RECOMPUTE)
    wrong_dataset_id = uuid4()

    response = test_client.post(
        f"/api/datasets/{wrong_dataset_id}/evaluation/runs/{run.evaluation_run_id}/recompute"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    recompute.assert_not_called()
