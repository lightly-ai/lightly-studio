from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.agent import tag_tools
from lightly_studio.agent.tag_tools import SelectDiverseArgs, ShowSamplesArgs, TagSamplesArgs
from lightly_studio.agent.ui_actions import SelectTagAction, ShowSamplesAction
from lightly_studio.resolvers import tag_resolver
from tests import helpers_resolvers
from tests.agent import helpers_agent

_EMBEDDINGS = {
    "a.jpg": [1.0, 0.0],
    "b.jpg": [0.99, 0.01],
    "c.jpg": [0.0, 1.0],
    "d.jpg": [0.01, 0.99],
}


def test_tag_samples(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(
        session=db_session, collection=collection, selected_sample_ids=[ids["a.jpg"], ids["c.jpg"]]
    )

    result = tag_tools.tag_samples(context, TagSamplesArgs(source="selection", tag_name=" tiger "))

    tag = tag_resolver.get_by_name(
        session=db_session, tag_name="tiger", collection_id=collection.collection_id
    )
    assert tag is not None
    assert sorted(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)) == (
        sorted([ids["a.jpg"], ids["c.jpg"]])
    )
    assert result == {"tag_name": "tiger", "tagged_count": 2}
    assert context.ui_actions == [SelectTagAction(tag_id=tag.tag_id, tag_name="tiger")]


def test_select_diverse(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = tag_tools.select_diverse(context, SelectDiverseArgs(n_samples=2, tag_name="diverse"))

    tag = tag_resolver.get_by_name(
        session=db_session, tag_name="diverse", collection_id=collection.collection_id
    )
    assert tag is not None
    selected = set(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id))
    # The two clusters are {a, b} and {c, d}. A diverse pair takes one sample of each.
    assert len(selected) == 2
    assert len(selected & {ids["a.jpg"], ids["b.jpg"]}) == 1
    assert result["selected_count"] == 2
    assert result["tag_name"] == "diverse"
    assert context.ui_actions == [SelectTagAction(tag_id=tag.tag_id, tag_name="diverse")]


def test_select_diverse__tag_exists(db_session: Session) -> None:
    collection, _ = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    helpers_resolvers.create_tag(
        session=db_session, collection_id=collection.collection_id, tag_name="diverse"
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="diverse"):
        tag_tools.select_diverse(context, SelectDiverseArgs(n_samples=2, tag_name="diverse"))


def test_show_samples(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)
    handle = context.result_store.put(
        collection_id=collection.collection_id, sample_ids=[ids["d.jpg"], ids["a.jpg"]]
    )

    result = tag_tools.show_samples(context, ShowSamplesArgs(source=handle))

    assert result == {"shown_count": 2}
    assert context.ui_actions == [ShowSamplesAction(sample_ids=[ids["d.jpg"], ids["a.jpg"]])]
