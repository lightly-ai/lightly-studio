from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPRECESSABLE_ENTITY,
)
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import SampleImage, create_images, create_tag


def create_dataset(
    client: TestClient,
    name: str = "example_dataset",
) -> str:
    """Helper function to create a dataset and return its ID."""
    dataset_data = {
        "name": name,
    }
    response = client.post("/api/datasets", json=dataset_data)
    assert response.status_code == HTTP_STATUS_CREATED, (
        f"Dataset creation failed: {response.json()}"
    )
    response_data: dict[str, Any] = response.json()
    dataset_id: str = response_data["dataset_id"]
    return dataset_id


def test_create_dataset(test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_dataset(client)

    # Validate the created dataset
    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_OK
    dataset = response.json()
    assert dataset["name"] == "example_dataset"


def test_create_dataset__invalid_data(test_client: TestClient) -> None:
    client = test_client
    # Attempt to create a dataset with invalid data (missing required fields)
    invalid_data = {
        "invalid_key": "example_dataset",
    }
    response = client.post("/api/datasets", json=invalid_data)
    assert response.status_code == HTTP_STATUS_UNPRECESSABLE_ENTITY


def test_create_dataset__duplicate_name(test_client: TestClient) -> None:
    client = test_client
    dataset_data = {"name": "example_dataset"}
    response = client.post("/api/datasets", json=dataset_data)
    assert response.status_code == HTTP_STATUS_CREATED

    # Attempt to create a dataset with already existing name conflicts
    response = client.post("/api/datasets", json=dataset_data)
    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_read_datasets(test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_dataset(client)

    response = client.get("/api/datasets")
    assert response.status_code == HTTP_STATUS_OK

    datasets = response.json()
    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset["dataset_id"] == dataset_id
    assert dataset["name"] == "example_dataset"


def test_read_dataset(test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_dataset(client)

    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["dataset_id"] == dataset_id
    assert dataset["name"] == "example_dataset"


def test_update_dataset(test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_dataset(client)

    # Update the dataset
    updated_data = {
        "name": "updated_dataset",
    }

    response = client.put(f"/api/datasets/{dataset_id}", json=updated_data)
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["name"] == "updated_dataset"


def test_delete_dataset(test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_dataset(client)

    # Delete the dataset
    response = client.delete(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "deleted"}

    # Verify the dataset is deleted
    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_export_dataset(db_session: Session, test_client: TestClient) -> None:
    client = test_client
    dataset_id = UUID(create_dataset(client))
    samples = create_images(
        db_session=db_session,
        dataset_id=dataset_id,
        images=[
            SampleImage(path="path/to/image0.jpg"),
            SampleImage(path="path/to/image1.jpg"),
            SampleImage(path="path/to/image2.jpg"),
        ],
    )

    # Tag two samples.
    tag = create_tag(session=db_session, dataset_id=dataset_id)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=samples[0].sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=samples[2].sample)

    # Export the dataset
    response = client.post(
        f"/api/datasets/{dataset_id}/export",
        json={"include": {"tag_ids": [str(tag.tag_id)]}},
    )
    assert response.status_code == HTTP_STATUS_OK

    lines = response.text.split("\n")
    assert lines == ["path/to/image0.jpg", "path/to/image2.jpg"]
