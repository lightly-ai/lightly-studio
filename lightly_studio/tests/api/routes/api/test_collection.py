from __future__ import annotations

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManager
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_images,
    create_samples_with_embeddings,
)


def test_read_collections(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id

    response = client.get("/api/collections")
    assert response.status_code == HTTP_STATUS_OK

    collections = response.json()
    assert len(collections) == 1
    collection = collections[0]
    assert collection["collection_id"] == str(collection_id)
    assert collection["name"] == "example_collection"


def test_read_collection(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id

    response = client.get(f"/api/collections/{collection_id}")
    assert response.status_code == HTTP_STATUS_OK

    collection = response.json()
    assert collection["collection_id"] == str(collection_id)
    assert collection["name"] == "example_collection"


def test_update_collection(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id

    # Update the collection
    updated_data = {
        "name": "updated_collection",
        "sample_type": "image",
    }

    response = client.put(f"/api/collections/{collection_id}", json=updated_data)
    assert response.status_code == HTTP_STATUS_OK

    collection = response.json()
    assert collection["name"] == "updated_collection"


def test_delete_collection(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id

    # Delete the collection
    response = client.delete(f"/api/collections/{collection_id}")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"status": "deleted"}

    # Verify the collection is deleted
    response = client.get(f"/api/collections/{collection_id}")
    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_read_root_collection(test_client: TestClient, db_session: Session) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id
    create_collection(
        session=db_session, collection_name="child", parent_collection_id=collection_id
    )

    response = client.get(f"/api/collections/{collection_id}/dataset")
    assert response.status_code == HTTP_STATUS_OK

    collection = response.json()
    assert collection["collection_id"] == str(collection_id)
    assert collection["name"] == "example_collection"


def test_read_collection_hierarchy(test_client: TestClient, db_session: Session) -> None:
    """Test collection hierarchy retrieval.

    - A (root)
      - B
        - C
      - D
    """
    client = test_client
    ds_a_id = create_collection(session=db_session, collection_name="root_collection").collection_id
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

    collections = response.json()
    assert len(collections) == 4
    assert collections[0]["collection_id"] == str(ds_a_id)
    assert collections[0]["name"] == "root_collection"
    assert collections[1]["collection_id"] == str(ds_b_id)
    assert collections[1]["name"] == "child_B"
    assert collections[2]["collection_id"] == str(ds_c_id)
    assert collections[2]["name"] == "child_C"
    assert collections[3]["collection_id"] == str(ds_d_id)
    assert collections[3]["name"] == "child_D"


def test_read_collection_hierarchy__multiple_root_collections(
    test_client: TestClient, db_session: Session
) -> None:
    client = test_client
    collection_1_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id
    collection_2_id = create_collection(
        session=db_session, collection_name="example_collection_2"
    ).collection_id

    response = client.get(f"/api/collections/{collection_1_id}/hierarchy")
    assert response.status_code == HTTP_STATUS_OK
    collections = response.json()
    assert collections[0]["collection_id"] == str(collection_1_id)

    response = client.get(f"/api/collections/{collection_2_id}/hierarchy")
    assert response.status_code == HTTP_STATUS_OK
    collections = response.json()
    assert collections[0]["collection_id"] == str(collection_2_id)


def test_read_collections_overview(test_client: TestClient, db_session: Session) -> None:
    """Test dashboard endpoint returns root collections with correct sample counts."""
    client = test_client

    # Create two root collections.
    collection_with_samples = create_collection(
        session=db_session, collection_name="collection_with_samples", sample_type=SampleType.IMAGE
    )
    collection_without_samples = create_collection(
        session=db_session,
        collection_name="collection_without_samples",
        sample_type=SampleType.VIDEO,
    )

    # Add samples to only one collection.
    create_images(
        db_session=db_session,
        collection_id=collection_with_samples.collection_id,
        images=[ImageStub(path="/path/to/image1.jpg"), ImageStub(path="/path/to/image2.jpg")],
    )

    # Call endpoint and assert length.
    response = client.get("/api/collections/overview")
    assert response.status_code == HTTP_STATUS_OK

    collections_resp = response.json()
    assert len(collections_resp) == 2

    # Verify collection with samples.
    ds_with_samples_resp = next(
        d
        for d in collections_resp
        if d["collection_id"] == str(collection_with_samples.collection_id)
    )
    assert ds_with_samples_resp["total_sample_count"] == 2
    assert ds_with_samples_resp["name"] == "collection_with_samples"
    assert ds_with_samples_resp["sample_type"] == "image"

    # Verify collection without samples.
    ds_without_samples_resp = next(
        d
        for d in collections_resp
        if d["collection_id"] == str(collection_without_samples.collection_id)
    )
    assert ds_without_samples_resp["total_sample_count"] == 0
    assert ds_without_samples_resp["name"] == "collection_without_samples"
    assert ds_without_samples_resp["sample_type"] == "video"


def test_has_embeddings(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    col_id = create_collection(session=db_session).collection_id
    embedding_model_id = create_embedding_model(
        session=db_session, collection_id=col_id
    ).embedding_model_id
    mock_get_model = mocker.patch.object(
        EmbeddingManager, "load_or_get_default_model", return_value=embedding_model_id
    )

    # Initially, the collection has no embeddings.
    response = test_client.get(f"/api/collections/{col_id!s}/has_embeddings")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() is False
    mock_get_model.assert_called_once_with(session=db_session, collection_id=col_id)
    mock_get_model.reset_mock()

    # Add an embedding to the collection.
    create_samples_with_embeddings(
        session=db_session,
        collection_id=col_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[(ImageStub(), [0.1, 0.2, 0.3])],
    )

    # Now, the collection should report having embeddings.
    response = test_client.get(f"/api/collections/{col_id!s}/has_embeddings")
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() is True
    mock_get_model.assert_called_once_with(session=db_session, collection_id=col_id)
