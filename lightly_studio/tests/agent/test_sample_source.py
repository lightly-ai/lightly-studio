from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.agent import sample_source
from lightly_studio.resolvers import tag_resolver
from tests import helpers_resolvers
from tests.agent import helpers_agent


def test_resolve_source__all(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = sample_source.resolve_source(context, "all")

    assert sorted(result) == sorted([ids["a.jpg"], ids["b.jpg"]])


def test_resolve_source__selection(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    context = helpers_agent.create_context(
        session=db_session, collection=collection, selected_sample_ids=[ids["b.jpg"]]
    )

    assert sample_source.resolve_source(context, " selection ") == [ids["b.jpg"]]


def test_resolve_source__tag(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection.collection_id, tag_name="cats"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[ids["a.jpg"]]
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    assert sample_source.resolve_source(context, "tag:cats") == [ids["a.jpg"]]


def test_resolve_source__result_handle(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file={"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)
    handle = context.result_store.put(
        collection_id=collection.collection_id, sample_ids=[ids["b.jpg"], ids["a.jpg"]]
    )

    assert sample_source.resolve_source(context, handle) == [ids["b.jpg"], ids["a.jpg"]]


def test_resolve_source__unknown_tag(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="There is no tag named 'dogs'"):
        sample_source.resolve_source(context, "tag:dogs")


def test_resolve_source__empty_selection(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="'selection' contains no samples"):
        sample_source.resolve_source(context, "selection")
