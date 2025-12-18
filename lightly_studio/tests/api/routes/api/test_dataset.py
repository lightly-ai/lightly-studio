from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images, create_tag


def test_read_datasets(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id

    response = client.get("/api/collections")
    assert response.status_code == HTTP_STATUS_OK

    datasets = response.json()
    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset["collection_id"] == str(dataset_id)
    assert dataset["name"] == "example_dataset"


def test_read_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id

    response = client.get(f"/api/collections/{collection_id}")
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["collection_id"] == str(collection_id)
    assert dataset["name"] == "example_dataset"


def test_update_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id

    # Update the dataset
    updated_data = {
        "name": "updated_dataset",
        "sample_type": "image",
    }

    response = client.put(f"/api/collections/{collection_id}", json=updated_data)
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["name"] == "updated_dataset"


def test_delete_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id

    # Delete the dataset
    response = client.delete(f"/api/collections/{collection_id}")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "deleted"}

    # Verify the dataset is deleted
    response = client.get(f"/api/collections/{collection_id}")
    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_read_root_dataset(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    dataset_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id
    create_collection(session=db_session, collection_name="child", parent_collection_id=dataset_id)

    response = client.get(f"/api/collections/{dataset_id}/dataset")
    assert response.status_code == HTTP_STATUS_OK

    dataset = response.json()
    assert dataset["collection_id"] == str(dataset_id)
    assert dataset["name"] == "example_dataset"


def test_read_dataset_hierarchy(test_client: TestClient, db_session: Session) -> None:
    """Test dataset hierarchy retrieval.

    - A (root)
      - B
        - C
      - D
    """
    client = test_client
    ds_a_id = create_collection(session=db_session, collection_name="root_dataset").collection_id
    ds_b_id = create_collection(
        session=db_session, collection_name="child_B", parent_collection_id=ds_a_id
    ).collection_id
    ds_c_id = create_collection(
        session=db_session, collection_name="child_C", parent_collection_id=ds_b_id
    ).collection_id
    ds_d_id = create_collection(
        session=db_session, collection_name="child_D", parent_collection_id=ds_a_id
    ).collection_id
    response = client.get(f"/api/collections/{ds_a_id}/hierarchy")
    assert response.status_code == HTTP_STATUS_OK

    datasets = response.json()
    assert len(datasets) == 4
    assert datasets[0]["collection_id"] == str(ds_a_id)
    assert datasets[0]["name"] == "root_dataset"
    assert datasets[1]["collection_id"] == str(ds_b_id)
    assert datasets[1]["name"] == "child_B"
    assert datasets[2]["collection_id"] == str(ds_c_id)
    assert datasets[2]["name"] == "child_C"
    assert datasets[3]["collection_id"] == str(ds_d_id)
    assert datasets[3]["name"] == "child_D"


def test_read_dataset_hierarchy__multiple_root_datasets(
    test_client: TestClient, db_session: Session
) -> None:
    client = test_client
    dataset_1_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id
    dataset_2_id = create_collection(
        session=db_session, collection_name="example_dataset_2"
    ).collection_id

    response = client.get(f"/api/collections/{dataset_1_id}/hierarchy")
    assert response.status_code == HTTP_STATUS_OK
    datasets = response.json()
    assert datasets[0]["collection_id"] == str(dataset_1_id)

    response = client.get(f"/api/collections/{dataset_2_id}/hierarchy")
    assert response.status_code == HTTP_STATUS_OK
    datasets = response.json()
    assert datasets[0]["collection_id"] == str(dataset_2_id)


def test_export_dataset(db_session: Session, test_client: TestClient) -> None:
    client = test_client
    dataset_id = create_collection(
        session=db_session, collection_name="example_dataset"
    ).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=dataset_id,
        images=[
            ImageStub(path="path/to/image0.jpg"),
            ImageStub(path="path/to/image1.jpg"),
            ImageStub(path="path/to/image2.jpg"),
        ],
    )

    # Tag two samples.
    tag = create_tag(session=db_session, collection_id=dataset_id)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=images[0].sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=images[2].sample)

    # Export the dataset
    response = client.post(
        f"/api/collections/{dataset_id}/export",
        json={"include": {"tag_ids": [str(tag.tag_id)]}},
    )
    assert response.status_code == HTTP_STATUS_OK

    lines = response.text.split("\n")
    assert lines == ["path/to/image0.jpg", "path/to/image2.jpg"]


def test_read_datasets_overview(test_client: TestClient, db_session: Session) -> None:
    """Test dashboard endpoint returns root datasets with correct sample counts."""
    client = test_client

    # Create two root datasets.
    dataset_with_samples = create_collection(
        session=db_session, collection_name="dataset_with_samples", sample_type=SampleType.IMAGE
    )
    dataset_without_samples = create_collection(
        session=db_session,
        collection_name="dataset_without_samples",
        sample_type=SampleType.VIDEO,
    )

    # Add samples to only one dataset.
    create_images(
        db_session=db_session,
        collection_id=dataset_with_samples.collection_id,
        images=[ImageStub(path="/path/to/image1.jpg"), ImageStub(path="/path/to/image2.jpg")],
    )

    # Call endpoint and assert length.
    response = client.get("/api/collections/overview")
    assert response.status_code == HTTP_STATUS_OK

    datasets_resp = response.json()
    assert len(datasets_resp) == 2

    # Verify dataset with samples.
    ds_with_samples_resp = next(
        d for d in datasets_resp if d["collection_id"] == str(dataset_with_samples.collection_id)
    )
    assert ds_with_samples_resp["total_sample_count"] == 2
    assert ds_with_samples_resp["name"] == "dataset_with_samples"
    assert ds_with_samples_resp["sample_type"] == "image"

    # Verify dataset without samples.
    ds_without_samples_resp = next(
        d for d in datasets_resp if d["collection_id"] == str(dataset_without_samples.collection_id)
    )
    assert ds_without_samples_resp["total_sample_count"] == 0
    assert ds_without_samples_resp["name"] == "dataset_without_samples"
    assert ds_without_samples_resp["sample_type"] == "video"
