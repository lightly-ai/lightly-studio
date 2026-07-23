from __future__ import annotations

import re
from unittest.mock import ANY
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.metadata import (
    HistogramView,
    MetadataInfoView,
    MetadataValueCountsView,
    MetadataValueCountView,
)
from lightly_studio.resolvers import image_resolver, metadata_resolver, tag_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_tag,
    fill_db_with_samples_and_embeddings,
)


def test_get_metadata_info(test_client: TestClient, mocker: MockerFixture) -> None:
    """Test get_metadata_info endpoint."""
    collection_id = uuid4()
    # Create mock metadata objects that will be returned by
    # get_all_metadata_keys_and_schema.
    mock_metadata = [
        MetadataInfoView(name="key1", type="string"),
        MetadataInfoView(
            name="key2",
            type="integer",
            min=0,
            max=100,
            histogram=HistogramView(bin_edges=[0.0, 50.0, 100.0], counts=[3, 7]),
        ),
        MetadataInfoView(name="key3", type="float", min=0.0, max=1.0),
    ]
    mocker.patch(
        "lightly_studio.api.routes.api.metadata.metadata_info_resolver.get_all_metadata_keys_and_schema",
        return_value=mock_metadata,
    )

    # Make API request
    response = test_client.get(f"/api/collections/{collection_id}/metadata/info")

    # Check response
    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert len(data) == len(mock_metadata)
    for i, metadata in enumerate(mock_metadata):
        assert data[i]["name"] == metadata.name
        assert data[i]["type"] == metadata.type
        assert data[i].get("min") == metadata.min
        assert data[i].get("max") == metadata.max
        if metadata.histogram is None:
            assert data[i].get("histogram") is None
        else:
            assert data[i]["histogram"]["bin_edges"] == metadata.histogram.bin_edges
            assert data[i]["histogram"]["counts"] == metadata.histogram.counts


def test_get_metadata_info__empty_response(test_client: TestClient, mocker: MockerFixture) -> None:
    """Test get_metadata_info endpoint with no metadata."""
    collection_id = uuid4()
    # Mock get_all_metadata_keys_and_schema to return an empty list.
    mocker.patch(
        "lightly_studio.api.routes.api.metadata.metadata_info_resolver.get_all_metadata_keys_and_schema",
        return_value=[],
    )

    # Make API request
    response = test_client.get(f"/api/collections/{collection_id}/metadata/info")

    # Check response
    assert response.status_code == HTTP_STATUS_OK
    data = response.json()
    assert data == []


def test_get_metadata_value_counts(test_client: TestClient, mocker: MockerFixture) -> None:
    collection_id = uuid4()
    resolver = mocker.patch(
        "lightly_studio.api.routes.api.metadata."
        "metadata_value_counts_resolver.get_metadata_value_counts",
        return_value={
            "city": MetadataValueCountsView(
                value_counts=[MetadataValueCountView(value="Zurich", count=2)],
                other_count=1,
                missing_count=3,
            )
        },
    )
    filters = {
        "sample_filter": {"metadata_filters": [{"key": "country", "op": "==", "value": "CH"}]}
    }

    response = test_client.post(
        f"/api/collections/{collection_id}/metadata/value-counts",
        json={"filters": filters},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "city": {
            "value_counts": [{"value": "Zurich", "count": 2}],
            "other_count": 1,
            "missing_count": 3,
        }
    }
    resolver.assert_called_once_with(session=ANY, collection_id=collection_id, filters=ANY)
    called_filters = resolver.call_args.kwargs["filters"]
    assert called_filters.model_dump(exclude_none=True) == {
        "filter_type": "image",
        "sample_filter": {
            "filter_type": "sample",
            "metadata_filters": [{"key": "country", "op": "==", "value": "CH"}],
        },
    }


def test_get_metadata_value_counts__optional_body(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    collection_id = uuid4()
    resolver = mocker.patch(
        "lightly_studio.api.routes.api.metadata."
        "metadata_value_counts_resolver.get_metadata_value_counts",
        return_value={},
    )

    response = test_client.post(f"/api/collections/{collection_id}/metadata/value-counts")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {}
    resolver.assert_called_once_with(session=ANY, collection_id=collection_id, filters=None)


def test_metadata_value_counts__openapi_models(test_client: TestClient) -> None:
    openapi = test_client.get("/openapi.json").json()
    schemas = openapi["components"]["schemas"]
    assert "MetadataValueCountView" in schemas
    assert "MetadataValueCountsView" in schemas


def test_metadata_filter__invalid_in_value_returns_422(test_client: TestClient) -> None:
    collection_id = uuid4()
    response = test_client.post(
        f"/api/collections/{collection_id}/metadata/value-counts",
        json={
            "filters": {
                "sample_filter": {"metadata_filters": [{"key": "city", "op": "in", "value": []}]}
            }
        },
    )

    assert response.status_code == 422


# TODO(Mihnea, 10/2025): Also add tests with passing `embedding_model_name` and/or `metadata_name`
#  in the body.
def test_compute_typicality_metadata(test_client: TestClient, db_session: Session) -> None:
    # Create collection with samples and embeddings
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )

    # Make API request with empty body (uses defaults)
    response = test_client.post(f"/api/collections/{collection_id}/metadata/typicality", json={})

    # Assert 204 No Content response
    assert response.status_code == 204
    assert response.text == ""

    # Verify all samples have typicality metadata.
    samples = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    ).samples

    for sample in samples:
        typicality_value = metadata_resolver.get_value_for_sample(
            session=db_session, sample_id=sample.sample_id, key="typicality"
        )
        assert typicality_value is not None
        assert isinstance(typicality_value, float)


def test_compute_similarity_metadata(test_client: TestClient, db_session: Session) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )
    query_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="query_tag")
    samples = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    ).samples
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=query_tag.tag_id,
        sample_ids=[samples[0].sample_id, samples[2].sample_id],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/metadata/similarity/{query_tag.tag_id}", json={}
    )

    assert response.status_code == 200
    metadata_name = response.text[1:-1]  # We strip the double-quotes
    metadate_regex = r"similarity_query_tag_\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"
    assert re.match(metadate_regex, metadata_name)

    samples = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    ).samples

    # Verify all samples have similarity metadata.
    for sample in samples:
        similarity_value = metadata_resolver.get_value_for_sample(
            session=db_session, sample_id=sample.sample_id, key=metadata_name
        )
        assert similarity_value is not None
        assert isinstance(similarity_value, float)


def test_compute_similarity_metadata_missing_query(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/metadata/similarity/{uuid4()}", json={}
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert "Query tag" in response.text
    assert "not found" in response.text


def test_compute_similarity_metadata_missing_embedding_model(
    test_client: TestClient, db_session: Session
) -> None:
    collection = create_collection(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/metadata/similarity/{uuid4()}", json={}
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert "Embedding model not found" in response.text
