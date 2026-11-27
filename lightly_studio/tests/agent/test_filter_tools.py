from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.agent import filter_tools
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.filter_tools import FindSamplesArgs
from lightly_studio.resolvers import metadata_resolver
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from tests import helpers_resolvers
from tests.agent import helpers_agent

_EMBEDDINGS = {"a.jpg": [1.0, 0.0], "b.jpg": [0.9, 0.1], "c.jpg": [0.0, 1.0]}

# The weather of each image, and the annotation classes on it.
_WEATHER = {"a.jpg": "rain", "b.jpg": "rain", "c.jpg": "sun"}
_CLASSES = {"a.jpg": ["car"], "b.jpg": ["bus"], "c.jpg": ["car"]}


def test_find_samples__metadata(db_session: Session) -> None:
    context, ids = _create_context(session=db_session)

    result = filter_tools.find_samples(
        context,
        FindSamplesArgs(metadata=[MetadataFilter(key="weather", op="==", value="rain")]),
    )

    assert result["count"] == 2
    assert set(_result_ids(context=context, handle=result["result"])) == {
        ids["a.jpg"],
        ids["b.jpg"],
    }


def test_find_samples__annotation_classes_any_of(db_session: Session) -> None:
    context, ids = _create_context(session=db_session)

    result = filter_tools.find_samples(context, FindSamplesArgs(annotation_classes=["car", "bus"]))

    assert result["count"] == 3
    assert set(_result_ids(context=context, handle=result["result"])) == set(ids.values())


def test_find_samples__metadata_and_class_within(db_session: Session) -> None:
    context, ids = _create_context(session=db_session, selected_file_names=["a.jpg", "c.jpg"])
    # The model sends the arguments as JSON.
    args = FindSamplesArgs.model_validate_json(
        '{"metadata": [{"key": "weather", "op": "in", "value": ["rain", "snow"]}],'
        ' "annotation_classes": ["car"], "within": "selection"}'
    )

    result = filter_tools.find_samples(context, args)

    assert result["count"] == 1
    assert _result_ids(context=context, handle=result["result"]) == [ids["a.jpg"]]


def test_find_samples__unknown_annotation_class(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match="no annotation class named 'truck'"):
        filter_tools.find_samples(context, FindSamplesArgs(annotation_classes=["truck"]))


def test_find_samples__no_condition(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match="at least one"):
        filter_tools.find_samples(context, FindSamplesArgs())


def _create_context(
    session: Session, selected_file_names: list[str] | None = None
) -> tuple[AgentContext, dict[str, UUID]]:
    """Create a collection with the weather and the annotation classes of the module."""
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=session, embeddings_by_file=_EMBEDDINGS
    )
    labels = {
        name: helpers_resolvers.create_annotation_label(
            session=session, root_collection_id=collection.collection_id, label_name=name
        )
        for name in ("car", "bus")
    }
    for file_name, sample_id in ids.items():
        metadata_resolver.set_value_for_sample(
            session=session, sample_id=sample_id, key="weather", value=_WEATHER[file_name]
        )
        for class_name in _CLASSES[file_name]:
            helpers_resolvers.create_annotation(
                session=session,
                collection_id=collection.collection_id,
                sample_id=sample_id,
                annotation_label_id=labels[class_name].annotation_label_id,
            )
    selected = [ids[file_name] for file_name in selected_file_names or []]
    context = helpers_agent.create_context(
        session=session, collection=collection, selected_sample_ids=selected
    )
    return context, ids


def _result_ids(context: AgentContext, handle: str) -> list[UUID]:
    return context.result_store.get(collection_id=context.collection.collection_id, handle=handle)
