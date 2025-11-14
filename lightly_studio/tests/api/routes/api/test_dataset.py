from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import ImageStub, create_dataset, create_images, create_tag


def test_read_datasets(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_dataset(session=db_session, dataset_name="example_dataset").dataset_id

    response = client.get("/api/datasets")
    assert response.status_code == HTTP_STATUS_OK

    datasets = response.json()
    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset["dataset_id"] == str(dataset_id)
    assert dataset["name"] == "example_dataset"


def test_read_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_dataset(session=db_session, dataset_name="example_dataset").dataset_id

    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["dataset_id"] == str(dataset_id)
    assert dataset["name"] == "example_dataset"


def test_update_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_dataset(session=db_session, dataset_name="example_dataset").dataset_id

    # Update the dataset
    updated_data = {
        "name": "updated_dataset",
        "sample_type": "image",
    }

    response = client.put(f"/api/datasets/{dataset_id}", json=updated_data)
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["name"] == "updated_dataset"


def test_delete_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_dataset(session=db_session, dataset_name="example_dataset").dataset_id

    # Delete the dataset
    response = client.delete(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "deleted"}

    # Verify the dataset is deleted
    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_read_root_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_dataset(session=db_session, dataset_name="example_dataset").dataset_id
    create_dataset(session=db_session, dataset_name="child", parent_dataset_id=dataset_id)

    response = client.get("/api/datasets/root_dataset")
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["dataset_id"] == str(dataset_id)
    assert dataset["name"] == "example_dataset"


def test_read_root_dataset__multiple_root_datasets(
    test_client: TestClient, db_session: Session
) -> None:
    client = test_client
    create_dataset(session=db_session, dataset_name="example_dataset")
    create_dataset(session=db_session, dataset_name="example_dataset_2")

    response = client.get("/api/datasets/root_dataset")
    assert response.status_code != HTTP_STATUS_OK


def test_export_dataset(db_session: Session, test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_dataset(session=db_session, dataset_name="example_dataset").dataset_id
    images = create_images(
        db_session=db_session,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="path/to/image0.jpg"),
            ImageStub(path="path/to/image1.jpg"),
            ImageStub(path="path/to/image2.jpg"),
        ],
    )

    # Tag two samples.
    tag = create_tag(session=db_session, dataset_id=dataset_id)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=images[0].sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=images[2].sample)

    # Export the dataset
    response = client.post(
        f"/api/datasets/{dataset_id}/export",
        json={"include": {"tag_ids": [str(tag.tag_id)]}},
    )
    assert response.status_code == HTTP_STATUS_OK

    lines = response.text.split("\n")
    assert lines == ["path/to/image0.jpg", "path/to/image2.jpg"]
