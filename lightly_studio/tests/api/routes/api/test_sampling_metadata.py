"""Metadata preparation and selection complete in a single API request."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.metadata import compute_similarity
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.resolvers import image_resolver, metadata_resolver, tag_resolver
from tests import helpers_resolvers


def test_sampling_metadata__typicality_creates_result_tag(
    test_client: TestClient, db_session: Session
) -> None:
    # Typicality uses 20 nearest neighbors, so the collection must be larger.
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=30, embedding_model_names=["test-model"]
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 3,
            "sampling_result_tag_name": "result",
            "strategies": [{"strategy_name": "weights", "metadata_key": "typicality"}],
            "metadata_computations": [{"kind": "typicality", "metadata_name": "typicality"}],
        },
    )

    assert response.status_code == 204, response.text
    tag = tag_resolver.get_by_name(
        session=db_session, collection_id=collection_id, tag_name="result"
    )
    assert tag is not None
    assert len(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)) == 3


def test_sampling_metadata__similarity_creates_result_tag(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=5, embedding_model_names=["test-model"]
    )
    sample_ids = list(
        image_resolver.get_sample_ids(session=db_session, collection_id=collection_id)
    )
    query_tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection_id, tag_name="query"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=query_tag.tag_id, sample_ids=sample_ids[:2]
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 3,
            "sampling_result_tag_name": "result",
            "strategies": [{"strategy_name": "weights", "metadata_key": "similarity"}],
            "metadata_computations": [
                {
                    "kind": "similarity",
                    "metadata_name": "similarity",
                    "query_tag_id": str(query_tag.tag_id),
                }
            ],
        },
    )

    assert response.status_code == 204, response.text
    tag = tag_resolver.get_by_name(
        session=db_session, collection_id=collection_id, tag_name="result"
    )
    assert tag is not None
    assert len(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)) == 3


@pytest.mark.parametrize("foreign_tag", [False, True])
def test_sampling_metadata__invalid_query_tag_rolls_back(
    test_client: TestClient, db_session: Session, foreign_tag: bool
) -> None:
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=30, embedding_model_names=["test-model"]
    )
    query_tag_id = uuid4()
    if foreign_tag:
        other_collection = helpers_resolvers.create_collection(session=db_session)
        query_tag_id = helpers_resolvers.create_tag(
            session=db_session, collection_id=other_collection.collection_id, tag_name="query"
        ).tag_id
    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 3,
            "sampling_result_tag_name": "result",
            "strategies": [{"strategy_name": "weights", "metadata_key": "typicality"}],
            "metadata_computations": [
                {"kind": "typicality", "metadata_name": "typicality"},
                {
                    "kind": "similarity",
                    "metadata_name": "similarity",
                    "query_tag_id": str(query_tag_id),
                },
            ],
        },
    )
    assert response.status_code == 400, response.text
    assert "Similarity query tag must belong" in response.text
    assert list(db_session.exec(select(SampleMetadataTable))) == []
    assert (
        tag_resolver.get_by_name(session=db_session, collection_id=collection_id, tag_name="result")
        is None
    )


def test_sampling_metadata__computation_failure_restores_metadata(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=30, embedding_model_names=["test-model"]
    )
    sample_ids = list(
        image_resolver.get_sample_ids(session=db_session, collection_id=collection_id)
    )
    metadata_resolver.bulk_update_metadata(
        session=db_session,
        sample_metadata=[(sample_ids[0], {"typicality": 42.0, "existing": "value"})],
    )
    query_tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection_id, tag_name="query"
    )
    mocker.patch.object(
        compute_similarity,
        "compute_similarity_metadata",
        side_effect=ValueError("Computation failed"),
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 3,
            "sampling_result_tag_name": "result",
            "strategies": [{"strategy_name": "weights", "metadata_key": "typicality"}],
            "metadata_computations": [
                {"kind": "typicality", "metadata_name": "typicality"},
                {
                    "kind": "similarity",
                    "metadata_name": "similarity",
                    "query_tag_id": str(query_tag.tag_id),
                },
            ],
        },
    )
    assert response.status_code == 400, response.text
    assert "Computation failed" in response.text
    metadata = list(db_session.exec(select(SampleMetadataTable)))
    assert len(metadata) == 1
    assert metadata[0].data == {"typicality": 42.0, "existing": "value"}
    assert (
        tag_resolver.get_by_name(session=db_session, collection_id=collection_id, tag_name="result")
        is None
    )


def test_sampling_metadata__video_similarity_rejected(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = helpers_resolvers.fill_db_with_video_samples_and_embeddings(
        session=db_session, n_samples=1, embedding_model_names=[]
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 1,
            "sampling_result_tag_name": "result",
            "strategies": [],
            "metadata_computations": [
                {"kind": "similarity", "metadata_name": "similarity", "query_tag_id": str(uuid4())}
            ],
        },
    )
    assert response.status_code == 400, response.text
    assert "Similarity is only available for image collections" in response.text


def test_sampling_metadata__missing_embedding_model(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=1, embedding_model_names=[]
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 1,
            "sampling_result_tag_name": "result",
            "strategies": [],
            "metadata_computations": [{"kind": "typicality", "metadata_name": "typicality"}],
        },
    )
    assert response.status_code == 400, response.text
    assert "has no default embedding model" in response.text
