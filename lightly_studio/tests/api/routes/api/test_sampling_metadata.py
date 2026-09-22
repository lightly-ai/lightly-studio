"""Metadata preparation and selection complete in a single API request."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.resolvers import image_resolver, tag_resolver
from tests import helpers_resolvers


@pytest.mark.parametrize("kind", ["typicality", "similarity"])
def test_sampling_metadata__creates_result_tag(
    test_client: TestClient, db_session: Session, kind: str
) -> None:
    # Typicality uses 20 nearest neighbors, so the collection must be larger.
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=30, embedding_model_names=["test-model"]
    )
    computation = {"kind": kind, "metadata_name": kind}
    if kind == "similarity":
        sample_ids = list(
            image_resolver.get_sample_ids(session=db_session, collection_id=collection_id)
        )
        query_tag = helpers_resolvers.create_tag(
            session=db_session, collection_id=collection_id, tag_name="query"
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session, tag_id=query_tag.tag_id, sample_ids=sample_ids[:2]
        )
        computation["query_tag_id"] = str(query_tag.tag_id)

    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 3,
            "sampling_result_tag_name": "result",
            "strategies": [{"strategy_name": "weights", "metadata_key": kind}],
            "metadata_computations": [computation],
        },
    )

    assert response.status_code == 204, response.text
    tag = tag_resolver.get_by_name(
        session=db_session, collection_id=collection_id, tag_name="result"
    )
    assert tag is not None
    assert len(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)) == 3
