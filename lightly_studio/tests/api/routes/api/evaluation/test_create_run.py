from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import evaluation_run_resolver
from tests.api.routes.api.evaluation import helpers
from tests.helpers_resolvers import create_collection


def test_create_evaluation_run__object_detection(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

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
    data = response.json()
    assert data["sample_count"] == 1
    assert data["gt_annotation_count"] == 1
    assert data["pred_annotation_count"] == 1
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=root.dataset_id
    )
    assert len(runs) == 1
    assert str(runs[0].id) == data["evaluation_run_id"]
    assert runs[0].name == "run-1"
    assert runs[0].task_type == EvaluationTaskType.OBJECT_DETECTION
    assert runs[0].config_json == {"iou_threshold": 0.7, "classwise": False}


def test_create_evaluation_run__generates_name_and_default_config(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(root.collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=root.dataset_id
    )
    assert len(runs) == 1
    assert runs[0].name.startswith("object_detection ")
    assert runs[0].config_json == {"iou_threshold": 0.5, "classwise": True}


def test_create_evaluation_run__classification(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(
        db_session, annotation_type=AnnotationType.CLASSIFICATION
    )

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "classification",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(root.collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json()["sample_count"] == 1
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=root.dataset_id
    )
    assert len(runs) == 1
    assert runs[0].task_type == EvaluationTaskType.CLASSIFICATION


def test_create_evaluation_run__respects_filter(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session, image_widths=(1920, 100))

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(root.collection_id),
            "filter": {"filter_type": "image", "width": {"min": 500}},
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    data = response.json()
    assert data["sample_count"] == 1
    assert data["gt_annotation_count"] == 1
    assert data["pred_annotation_count"] == 1


def test_create_evaluation_run__same_source(test_client: TestClient, db_session: Session) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "gt",
            "collection_id": str(root.collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "must be different" in response.json()["error"]


def test_create_evaluation_run__wrong_annotation_type(
    test_client: TestClient, db_session: Session
) -> None:
    # Sources contain object-detection annotations, but a classification run is requested.
    root = helpers.create_dataset_with_annotations(db_session)

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "classification",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(root.collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "classification" in response.json()["error"]


def test_create_evaluation_run__unknown_source(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "nonexistent",
            "pred_annotation_source": "pred",
            "collection_id": str(root.collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "not found" in response.json()["error"]


def test_create_evaluation_run__collection_not_found(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)

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


def test_create_evaluation_run__non_image_collection(
    test_client: TestClient, db_session: Session
) -> None:
    root = helpers.create_dataset_with_annotations(db_session)
    annotation_collection = create_collection(
        session=db_session,
        collection_name="other_annotations",
        parent_collection_id=root.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/datasets/{root.dataset_id}/evaluation/runs",
        json={
            "task_type": "object_detection",
            "gt_annotation_source": "gt",
            "pred_annotation_source": "pred",
            "collection_id": str(annotation_collection.collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "image collections" in response.json()["error"]
