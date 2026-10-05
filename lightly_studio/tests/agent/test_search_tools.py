from __future__ import annotations

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.agent import search_tools
from lightly_studio.agent.search_tools import (
    FindSimilarArgs,
    GetCollectionOverviewArgs,
    SearchByTextArgs,
)
from lightly_studio.embed import embed_samples
from tests import helpers_resolvers
from tests.agent import helpers_agent

# Three images: `a` and `b` point almost the same way, `c` is orthogonal to `a`.
_EMBEDDINGS = {"a.jpg": [1.0, 0.0], "b.jpg": [0.9, 0.1], "c.jpg": [0.0, 1.0]}


def test_get_collection_overview(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    helpers_resolvers.create_tag(
        session=db_session, collection_id=collection.collection_id, tag_name="cats"
    )
    context = helpers_agent.create_context(
        session=db_session, collection=collection, selected_sample_ids=[ids["a.jpg"]]
    )

    overview = search_tools.get_collection_overview(context, GetCollectionOverviewArgs())

    assert overview == {
        "collection_name": collection.name,
        "sample_type": "image",
        "sample_count": 3,
        "selected_sample_count": 1,
        "has_embeddings": True,
        "tags": ["cats"],
        "annotation_labels": [],
    }


def test_search_by_text(db_session: Session, mocker: MockerFixture) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    mocker.patch.object(embed_samples, "embed_text_for_collection", return_value=[1.0, 0.0])
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = search_tools.search_by_text(context, SearchByTextArgs(query="tiger", limit=2))

    assert result["count"] == 2
    assert [match["file_name"] for match in result["best_matches"]] == ["a.jpg", "b.jpg"]
    assert result["best_matches"][0]["similarity"] == pytest.approx(1.0, abs=1e-3)
    assert context.result_store.get(
        collection_id=collection.collection_id, handle=result["result"]
    ) == [ids["a.jpg"], ids["b.jpg"]]


def test_search_by_text__within(db_session: Session, mocker: MockerFixture) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    mocker.patch.object(embed_samples, "embed_text_for_collection", return_value=[1.0, 0.0])
    context = helpers_agent.create_context(
        session=db_session, collection=collection, selected_sample_ids=[ids["c.jpg"]]
    )

    result = search_tools.search_by_text(
        context, SearchByTextArgs(query="tiger", limit=10, within="selection")
    )

    assert result["count"] == 1
    assert result["best_matches"][0]["file_name"] == "c.jpg"


def test_find_similar_samples(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(
        session=db_session, collection=collection, selected_sample_ids=[ids["a.jpg"]]
    )

    result = search_tools.find_similar_samples(
        context, FindSimilarArgs(source="selection", limit=1)
    )

    # The query sample `a` is left out, so its nearest neighbour `b` comes first.
    assert result["count"] == 1
    assert result["best_matches"][0]["file_name"] == "b.jpg"


def test_aggregate_query_embedding__single() -> None:
    embedding = np.array([3.0, 4.0], dtype=np.float32)

    result = search_tools.aggregate_query_embedding(embeddings=[embedding])

    # One query sample keeps its direction.
    assert np.asarray(result) / np.linalg.norm(result) == pytest.approx([0.6, 0.8])


def test_aggregate_query_embedding__two() -> None:
    embeddings = [np.array([1.0, 0.0], dtype=np.float32), np.array([0.0, 1.0], dtype=np.float32)]

    result = search_tools.aggregate_query_embedding(embeddings=embeddings)

    # Two orthogonal unit vectors of the same weight point to the diagonal.
    assert np.asarray(result) / np.linalg.norm(result) == pytest.approx([0.7071, 0.7071], abs=1e-3)


def test_aggregate_query_embedding__skips_zero_vectors() -> None:
    embeddings = [np.array([0.0, 0.0], dtype=np.float32), np.array([0.0, 2.0], dtype=np.float32)]

    result = search_tools.aggregate_query_embedding(embeddings=embeddings)

    assert result == pytest.approx([0.0, 1.0])


def test_aggregate_query_embedding__only_zero_vectors() -> None:
    with pytest.raises(ValueError, match="only zero embeddings"):
        search_tools.aggregate_query_embedding(embeddings=[np.array([0.0, 0.0], dtype=np.float32)])
