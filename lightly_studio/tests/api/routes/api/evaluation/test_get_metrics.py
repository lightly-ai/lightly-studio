from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.evaluation.image_dataset_evaluate import (
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import tag_resolver
from lightly_studio.services import evaluation_service
from tests.api.routes.api.evaluation import helpers
from tests.helpers_resolvers import create_tag
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_get_evaluation_runs_metrics(test_client: TestClient, db_session: Session) -> None:
    # The ground truth and prediction boxes are identical, so every metric is 1.
    root = helpers.create_dataset_with_annotations(db_session)
    run_with_ap = _run_object_detection(
        session=db_session, root=root, name="with-ap", compute_average_precision=True
    )
    run_without_ap = _run_object_detection(
        session=db_session, root=root, name="without-ap", compute_average_precision=False
    )

    response = test_client.get(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(run_without_ap), str(run_with_ap)]},
    )

    assert response.status_code == HTTP_STATUS_OK
    body = response.json()
    assert [view["evaluation_run_id"] for view in body] == [
        str(run_without_ap),
        str(run_with_ap),
    ]
    assert body[0]["metrics"]["precision"] == pytest.approx(1.0)
    assert body[0]["metrics"]["mean_average_precision"] is None
    assert body[1]["metrics"]["mean_average_precision"] == pytest.approx(1.0)
    assert body[0]["evaluated_sample_count"] == 1
    assert body[0]["evaluated_sample_set_hash"] == body[1]["evaluated_sample_set_hash"]


def test_get_evaluation_runs_metrics__semantic_segmentation_returns_422(
    test_client: TestClient, db_session: Session
) -> None:
    run = evaluation_sample_metric_helpers.create_run(session=db_session)
    run.task_type = EvaluationTaskType.SEMANTIC_SEGMENTATION
    db_session.commit()

    response = test_client.get(
        f"/api/datasets/{run.dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(run.id)]},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert "semantic_segmentation" in response.json()["error"]


def test_get_evaluation_runs_metrics__unknown_run_returns_404(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    unknown_run_id = uuid4()

    response = test_client.get(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(unknown_run_id)]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert str(unknown_run_id) in response.json()["error"]


def test_get_evaluation_runs_metrics__run_of_other_dataset_returns_404(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    run_id = _run_object_detection(
        session=db_session, root=root, name="run-1", compute_average_precision=False
    )
    other_dataset_id = uuid4()

    response = test_client.get(
        f"/api/datasets/{other_dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(run_id)]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_evaluation_runs_metrics__no_run_ids_returns_422(test_client: TestClient) -> None:
    response = test_client.get(f"/api/datasets/{uuid4()}/evaluation/runs/metrics")

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_get_evaluation_runs_metrics__tag_slices(
    test_client: TestClient, db_session: Session
) -> None:
    root, hit_id, miss_id = helpers.create_dataset_with_hit_and_miss(db_session=db_session)
    run_id = _run_object_detection(
        session=db_session, root=root, name="run-1", compute_average_precision=True
    )
    tags = {
        name: create_tag(session=db_session, collection_id=root.collection_id, tag_name=name)
        for name in ("hits", "misses")
    }
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tags["hits"].tag_id, sample_ids=[hit_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tags["misses"].tag_id, sample_ids=[miss_id]
    )

    response = test_client.get(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/metrics",
        params={
            "run_ids": [str(run_id)],
            "tag_ids": [str(tags["misses"].tag_id), str(tags["hits"].tag_id)],
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    slices = response.json()[0]["slices"]
    assert [entry["tag_name"] for entry in slices] == ["misses", "hits"]
    assert [entry["evaluated_sample_count"] for entry in slices] == [1, 1]
    assert slices[0]["metrics"]["precision"] == pytest.approx(0.0)
    assert slices[1]["metrics"]["precision"] == pytest.approx(1.0)


def test_get_evaluation_runs_metrics__no_tags_no_slices(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session=db_session)
    run_id = _run_object_detection(
        session=db_session, root=root, name="run-1", compute_average_precision=False
    )

    response = test_client.get(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(run_id)]},
    )

    assert response.json()[0]["slices"] == []


def test_get_evaluation_runs_metrics__unknown_tag_returns_404(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session=db_session)
    run_id = _run_object_detection(
        session=db_session, root=root, name="run-1", compute_average_precision=False
    )

    response = test_client.get(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(run_id)], "tag_ids": [str(uuid4())]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_evaluation_runs_metrics__tag_of_other_dataset_returns_404(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session=db_session)
    run_id = _run_object_detection(
        session=db_session, root=root, name="run-1", compute_average_precision=False
    )
    other_root = helpers.create_dataset_with_annotations(db_session=db_session)
    other_tag = create_tag(session=db_session, collection_id=other_root.collection_id)

    response = test_client.get(
        f"/api/datasets/{root.dataset_id}/evaluation/runs/metrics",
        params={"run_ids": [str(run_id)], "tag_ids": [str(other_tag.tag_id)]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def _run_object_detection(
    session: Session, root: CollectionTable, name: str, compute_average_precision: bool
) -> UUID:
    result = evaluation_service.run_evaluation(
        session=session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(compute_average_precision=compute_average_precision),
        name=name,
    )
    return result.evaluation_run_id
