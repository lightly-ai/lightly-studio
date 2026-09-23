"""Tests for the per-annotation evaluation metrics info route."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
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
                metrics={"iou": 0.75},
                gt_annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    response = test_client.get(
        f"/api/collections/{run.gt_annotation_collection_id}/evaluation/metrics/annotation/info"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
        {
            "run_id": str(run.id),
            "run_name": "detection eval",
            "task_type": "object_detection",
            "metrics": [{"metric_name": "iou"}],
        }
    ]
