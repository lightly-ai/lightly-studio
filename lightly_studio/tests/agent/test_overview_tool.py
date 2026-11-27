from __future__ import annotations

from sqlmodel import Session

from lightly_studio.agent import overview_tool
from lightly_studio.agent.overview_tool import GetCollectionOverviewArgs, ListAnnotationClassesArgs
from lightly_studio.resolvers import metadata_resolver
from tests import helpers_resolvers
from tests.agent import helpers_agent

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

    overview = overview_tool.get_collection_overview(context, GetCollectionOverviewArgs())

    assert overview == {
        "collection_name": collection.name,
        "sample_type": "image",
        "sample_count": 3,
        "selected_sample_count": 1,
        "tags": ["cats"],
        "embedding_models": [{"name": "example_embedding_model", "is_default": True}],
        "metadata": [],
        "annotation_classes": [],
    }


def test_get_collection_overview__metadata(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    for file_name, weather, typicality in [
        ("a.jpg", "rain", 0.25),
        ("b.jpg", "rain", 0.5),
        ("c.jpg", "sun", 0.75),
    ]:
        metadata_resolver.set_value_for_sample(
            session=db_session, sample_id=ids[file_name], key="weather", value=weather
        )
        metadata_resolver.set_value_for_sample(
            session=db_session, sample_id=ids[file_name], key="typicality", value=typicality
        )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    overview = overview_tool.get_collection_overview(context, GetCollectionOverviewArgs())

    facts_by_key = {fact["key"]: fact for fact in overview["metadata"]}
    assert facts_by_key == {
        "weather": {
            "key": "weather",
            "type": "string",
            "top_values": [{"value": "rain", "count": 2}, {"value": "sun", "count": 1}],
        },
        "typicality": {"key": "typicality", "type": "float", "min": 0.25, "max": 0.75},
    }


def test_get_collection_overview__annotation_classes(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    car = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    bus = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="bus"
    )
    # Two cars on `a` count as one sample.
    for file_name, label in [("a.jpg", car), ("a.jpg", car), ("b.jpg", car), ("c.jpg", bus)]:
        helpers_resolvers.create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=ids[file_name],
            annotation_label_id=label.annotation_label_id,
        )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    overview = overview_tool.get_collection_overview(context, GetCollectionOverviewArgs())

    assert overview["annotation_classes"] == [
        {"name": "car", "sample_count": 2},
        {"name": "bus", "sample_count": 1},
    ]


def test_list_annotation_classes(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    clock = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="clock"
    )
    person = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="person"
    )
    for file_name, label in [("a.jpg", person), ("b.jpg", person), ("c.jpg", clock)]:
        helpers_resolvers.create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=ids[file_name],
            annotation_label_id=label.annotation_label_id,
        )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = overview_tool.list_annotation_classes(context, ListAnnotationClassesArgs())

    assert result == {
        "annotation_classes": [
            {"name": "person", "sample_count": 2},
            {"name": "clock", "sample_count": 1},
        ]
    }


def test_list_annotation_classes__no_annotations(db_session: Session) -> None:
    collection, _ = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = overview_tool.list_annotation_classes(context, ListAnnotationClassesArgs())

    assert result == {"annotation_classes": []}
