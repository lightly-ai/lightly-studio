"""Exercise evaluation parameter updates through the API."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from tests.api.routes.api.evaluation import helpers


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({}, 200),
        ({"config": {"iou_threshold": -0.1}}, 400),
        ({"config": {"iou_threshold": 1.1}}, 400),
        ({"config": {"iou_treshold": 0.75}}, 400),
        ({"config": {"iou_threshold": 0.75, "class_wise": False}}, 400),
        ({"config": None}, 422),
        ({"name": "updated"}, 422),
        ({"task_type": "classification"}, 422),
        ({"gt_annotation_source": "missing"}, 422),
        ({"pred_annotation_source": "gt"}, 422),
        ({"dataset_id": str(uuid4())}, 404),
        ({"run_id": str(uuid4())}, 404),
    ],
)
def test_update_run(
    test_client: TestClient, db_session: Session, changes: dict[str, Any], status: int
) -> None:
    root = helpers.create_dataset_with_annotations(
        db_session, annotation_data={"x": 50, "y": 50, "width": 20, "height": 20}
    )
    box = db_session.exec(select(ObjectDetectionAnnotationTable)).first()
    assert box is not None
    box.x = 54  # IoU is 2/3: matches at 0.5, but not at 0.75.
    db_session.commit()
    url = f"/api/datasets/{root.dataset_id}/evaluation/runs"
    created = test_client.post(
        url,
        json={
            "name": "original",
            "collection_id": str(root.collection_id),
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "config": {"iou_threshold": 0.5, "classwise": True},
        },
    )
    assert created.status_code == 201
    run_id = created.json()["evaluation_run_id"]
    before = test_client.get(url).json()
    settings = {
        "config": {"iou_threshold": 0.75, "classwise": False, "compute_average_precision": False}
    }
    changes = dict(changes)
    dataset_id = changes.pop("dataset_id", str(root.dataset_id))
    target_id = changes.pop("run_id", run_id)
    target_url = f"/api/datasets/{dataset_id}/evaluation/runs/{target_id}"
    response = test_client.put(target_url, json={**settings, **changes})
    assert response.status_code == status
    after = test_client.get(url).json()
    if status != 200:
        assert after == before
        return
    assert response.json() == created.json()
    assert after == [{**before[0], "evaluation_run_configuration": settings["config"]}]
    metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=UUID(run_id)
    )
    assert {metric.metric_name: metric.value for metric in metrics} == {
        "tp": 0.0,
        "fp": 1.0,
        "fn": 1.0,
    }
    assert test_client.put(target_url, json=settings).status_code == 200
