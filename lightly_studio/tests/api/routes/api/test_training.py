from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.services.training_service import helpers


def test_get_training_runs__no_runs(test_client: TestClient, db_session: Session) -> None:
    dataset = helpers.create_training_dataset(session=db_session)

    response = test_client.get(f"/api/collections/{dataset.collection.collection_id}/training/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_create_training_run__same_tags(test_client: TestClient, db_session: Session) -> None:
    dataset = helpers.create_training_dataset(session=db_session)

    response = test_client.post(
        f"/api/collections/{dataset.collection.collection_id}/training/runs",
        json={
            "train_tag_id": str(dataset.train_tag_id),
            "val_tag_id": str(dataset.train_tag_id),
            "gt_annotation_collection_id": str(dataset.gt_annotation_collection_id),
        },
    )

    assert response.status_code == 400
    assert "must be different" in response.text
