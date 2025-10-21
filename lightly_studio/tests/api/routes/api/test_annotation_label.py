from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)


def create_annotation_label(client: TestClient) -> tuple[str, dict[str, str]]:
    """Helper function to create an annotation label and return its ID."""
    input_label = {
        "annotation_label_name": "Test Label",
    }

    new_label_result = client.post(
        "/api/annotation_labels",
        json=input_label,
    )
    assert new_label_result.status_code == HTTP_STATUS_CREATED
    return new_label_result.json()["annotation_label_id"], input_label


def test_create_annotation_label(test_client: TestClient) -> None:
    client = test_client
    label_id, input_label = create_annotation_label(client)

    # Validate the created annotation label
    assert label_id is not None
    assert input_label["annotation_label_name"] == "Test Label"


def test_get_annotation_labels(test_client: TestClient) -> None:
    client = test_client
    create_annotation_label(client)

    labels_result = client.get("/api/annotation_labels")
    assert labels_result.status_code == HTTP_STATUS_OK

    label = labels_result.json()[0]
    assert label["annotation_label_name"] == "Test Label"


def test_get_annotation_label(test_client: TestClient) -> None:
    client = test_client
    label_id, input_label = create_annotation_label(client)

    label_result = client.get(f"/api/annotation_labels/{label_id}")
    assert label_result.status_code == HTTP_STATUS_OK

    label = label_result.json()
    assert label["annotation_label_name"] == input_label["annotation_label_name"]


def test_update_annotation_label(test_client: TestClient) -> None:
    client = test_client
    label_id, input_label = create_annotation_label(client)

    updated_label = {
        "annotation_label_id": label_id,
        "annotation_label_name": "Updated Label",
    }

    label_result = client.put(
        f"/api/annotation_labels/{label_id}",
        json=updated_label,
    )
    assert label_result.status_code == HTTP_STATUS_OK

    label = label_result.json()
    assert label["annotation_label_name"] == updated_label["annotation_label_name"]


def test_delete_annotation_label(test_client: TestClient) -> None:
    client = test_client
    label_id, _ = create_annotation_label(client)

    label_result = client.delete(f"/api/annotation_labels/{label_id}")
    assert label_result.status_code == HTTP_STATUS_OK
    assert label_result.json() == {"status": "deleted"}

    label_result = client.get(f"/api/annotation_labels/{label_id}")
    assert label_result.status_code == HTTP_STATUS_NOT_FOUND
