from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.models.metadata import MetadataInfoView
from lightly_studio.resolvers import image_resolver, metadata_resolver, tag_resolver
from tests.helpers_resolvers import create_tag, fill_db_with_samples_and_embeddings


def test_get_metadata_info(test_client: TestClient, mocker: MockerFixture) -> None:
    """Test get_metadata_info endpoint."""
    dataset_id = uuid4()
    # Create mock metadata objects that will be returned by
    # get_all_metadata_keys_and_schema.
    mock_metadata = [
        MetadataInfoView(name="key1", type="string"),
        MetadataInfoView(name="key2", type="integer", min=0, max=100),
        MetadataInfoView(name="key3", type="float", min=0.0, max=1.0),
    ]
    mocker.patch(
        "lightly_studio.api.routes.api.metadata.get_all_metadata_keys_and_schema",
        return_value=mock_metadata,
    )

    # Make API request
    response = test_client.get(f"/api/datasets/{dataset_id}/metadata/info")

    # Check response
    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert len(data) == len(mock_metadata)
    for i, metadata in enumerate(mock_metadata):
        assert data[i]["name"] == metadata.name
        assert data[i]["type"] == metadata.type
        assert data[i].get("min") == metadata.min
        assert data[i].get("max") == metadata.max


def test_get_metadata_info__empty_response(test_client: TestClient, mocker: MockerFixture) -> None:
    """Test get_metadata_info endpoint with no metadata."""
    dataset_id = uuid4()
    # Mock get_all_metadata_keys_and_schema to return an empty list.
    mocker.patch(
        "lightly_studio.api.routes.api.metadata.get_all_metadata_keys_and_schema",
        return_value=[],
    )

    # Make API request
    response = test_client.get(f"/api/datasets/{dataset_id}/metadata/info")

    # Check response
    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data == []


# TODO(Mihnea, 10/2025): Also add tests with passing `embedding_model_name` and/or `metadata_name`
#  in the body.
def test_compute_typicality_metadata(test_client: TestClient, db_session: Session) -> None:
    """Test compute typicality metadata endpoint."""
    # Create dataset with samples and embeddings
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )

    # Make API request with empty body (uses defaults)
    response = test_client.post(f"/api/datasets/{dataset_id}/metadata/typicality", json={})

    # Assert 204 No Content response
    assert response.status_code == 204
    assert response.text == ""

    # Verify all samples have typicality metadata.
    samples = image_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset_id
    ).samples

    assert len(samples) == 10

    for sample in samples:
        typicality_value = metadata_resolver.get_value_for_sample(
            session=db_session, sample_id=sample.sample_id, key="typicality"
        )
        assert typicality_value is not None
        assert isinstance(typicality_value, float)


def test_compute_similarity_metadata(test_client: TestClient, db_session: Session) -> None:
    """Test compute similarity metadata endpoint."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )
    query_tag = create_tag(session=db_session, dataset_id=dataset_id, tag_name="query_tag")
    samples = image_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset_id
    ).samples
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=query_tag.tag_id,
        sample_ids=[samples[0].sample_id, samples[2].sample_id],
    )

    response = test_client.post(
        f"/api/datasets/{dataset_id}/metadata/similarity", json={"query_tag_name": "query_tag"}
    )

    assert response.status_code == 200
    metadata_name = response.text[1:-1]  # We strip the double-quotes
    assert metadata_name.startswith("similarity_query_tag_20")

    samples = image_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset_id
    ).samples
    assert len(samples) == 10

    # Verify all samples have similarity metadata.
    for sample in samples:
        similarity_value = metadata_resolver.get_value_for_sample(
            session=db_session, sample_id=sample.sample_id, key=metadata_name
        )
        assert similarity_value is not None
        assert isinstance(similarity_value, float)
