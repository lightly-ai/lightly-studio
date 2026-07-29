"""Tests for the per-annotation evaluation metrics info route."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)


def test_get_evaluation_annotation_metrics_info(
    test_client: TestClient,
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id, name="detection eval")
    image = create_image(session=db_session, collection_id=root.collection_id)
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.75, "disagreement": 0.25},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    # Both sides of the pairing offer the same options.
    for collection_id in (run.gt_annotation_collection_id, run.pred_annotation_collection_id):
        info = _get_info(test_client=test_client, collection_id=collection_id)

        assert info == [
            {
                "run_id": str(run.id),
                "run_name": "detection eval",
                "task_type": "object_detection",
                "metric_names": ["disagreement", "iou"],
            }
        ]


def test_get_evaluation_annotation_metrics_info__omits_run_without_metric_names(
    test_client: TestClient,
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    image = create_image(session=db_session, collection_id=root.collection_id)
    # A false negative writes a row carrying no metric name, which is not a sort option.
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            FalseNegativeMetricStub(
                sample_id=image.sample_id,
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    info = _get_info(test_client=test_client, collection_id=run.gt_annotation_collection_id)

    assert info == []


def test_get_evaluation_annotation_metrics_info__omits_run_without_annotation_metrics(
    test_client: TestClient,
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    run = create_run(session=db_session, collection_id=root.collection_id)

    info = _get_info(test_client=test_client, collection_id=run.gt_annotation_collection_id)

    assert info == []


def test_get_evaluation_annotation_metrics_info__omits_run_of_other_source(
    test_client: TestClient,
    db_session: Session,
) -> None:
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    run = create_run(session=db_session, collection_id=root.collection_id)
    other_run = create_run(session=db_session, collection_id=root.collection_id, name="other run")
    image = create_image(session=db_session, collection_id=root.collection_id)
    create_annotation_metrics(
        session=db_session,
        run_id=other_run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"iou": 0.75},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    info = _get_info(test_client=test_client, collection_id=run.gt_annotation_collection_id)

    assert info == []


def _get_info(test_client: TestClient, collection_id: UUID) -> list[Any]:
    response = test_client.get(
        f"/api/collections/{collection_id}/evaluation/metrics/annotation/info"
    )
    assert response.status_code == HTTP_STATUS_OK
    info: list[Any] = response.json()
    return info
