from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.agent import selection_tools
from lightly_studio.agent.selection_tools import ComputeMetadataArgs, RunSelectionArgs
from lightly_studio.agent.ui_actions import SelectTagAction
from lightly_studio.resolvers import metadata_resolver, tag_resolver
from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDiversityStrategy,
    MetadataBalancingStrategy,
    MetadataWeightingStrategy,
)
from tests import helpers_resolvers
from tests.agent import helpers_agent

# Two clusters: {a, b} and {c, d}.
_EMBEDDINGS = {
    "a.jpg": [1.0, 0.0],
    "b.jpg": [0.99, 0.01],
    "c.jpg": [0.0, 1.0],
    "d.jpg": [0.01, 0.99],
}


def test_compute_metadata__typicality(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = selection_tools.compute_metadata(
        context, ComputeMetadataArgs(kind="typicality", metadata_name="typicality")
    )

    assert result == {"metadata_name": "typicality", "computed": "typicality"}
    for sample_id in ids.values():
        value = metadata_resolver.get_value_for_sample(
            session=db_session, sample_id=sample_id, key="typicality"
        )
        assert isinstance(value, float)


def test_compute_metadata__similarity_without_query_tag(db_session: Session) -> None:
    collection, _ = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="needs a query_tag"):
        selection_tools.compute_metadata(
            context, ComputeMetadataArgs(kind="similarity", metadata_name="sim")
        )


def test_compute_metadata__similarity_unknown_tag(db_session: Session) -> None:
    collection, _ = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="no tag named 'night'"):
        selection_tools.compute_metadata(
            context, ComputeMetadataArgs(kind="similarity", metadata_name="sim", query_tag="night")
        )


def test_run_selection__combined_strategies(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    # In each cluster, the weighting prefers one sample: `b` and `d`.
    for file_name, score in [("a.jpg", 0.0), ("b.jpg", 1.0), ("c.jpg", 0.0), ("d.jpg", 1.0)]:
        metadata_resolver.set_value_for_sample(
            session=db_session, sample_id=ids[file_name], key="score", value=score
        )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = selection_tools.run_selection(
        context,
        RunSelectionArgs(
            n_samples=2,
            tag_name=" picked ",
            strategies=[
                EmbeddingDiversityStrategy(strength=1.0),
                MetadataWeightingStrategy(metadata_key="score", strength=2.0),
            ],
        ),
    )

    tag = tag_resolver.get_by_name(
        session=db_session, tag_name="picked", collection_id=collection.collection_id
    )
    assert tag is not None
    selected = set(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id))
    assert selected == {ids["b.jpg"], ids["d.jpg"]}
    assert result == {
        "tag_name": "picked",
        "selected_count": 2,
        "result": result["result"],
        "strategies": ["diversity x1", "weights(score) x2"],
    }
    assert (
        set(
            context.result_store.get(
                collection_id=collection.collection_id, handle=result["result"]
            )
        )
        == selected
    )
    assert context.ui_actions == [SelectTagAction(tag_id=tag.tag_id, tag_name="picked")]


def test_run_selection__achieved_distribution(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    for file_name, weather in [
        ("a.jpg", "rain"),
        ("b.jpg", "sun"),
        ("c.jpg", "sun"),
        ("d.jpg", "sun"),
    ]:
        metadata_resolver.set_value_for_sample(
            session=db_session, sample_id=ids[file_name], key="weather", value=weather
        )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = selection_tools.run_selection(
        context,
        RunSelectionArgs(
            n_samples=2,
            tag_name="balanced",
            strategies=[
                MetadataBalancingStrategy(
                    metadata_key="weather", target_distribution={"rain": 0.5, "sun": 0.5}
                )
            ],
        ),
    )

    assert result["achieved_distributions"] == {
        "weather": {
            "target": {"rain": 0.5, "sun": 0.5},
            "values": [
                {"value": "rain", "count": 1, "share": 0.5},
                {"value": "sun", "count": 1, "share": 0.5},
            ],
        }
    }


def test_run_selection__achieved_class_distribution(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    labels = {
        name: helpers_resolvers.create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id, label_name=name
        )
        for name in ("car", "bus")
    }
    for file_name, class_name in [
        ("a.jpg", "car"),
        ("b.jpg", "car"),
        ("c.jpg", "car"),
        ("d.jpg", "bus"),
    ]:
        helpers_resolvers.create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=ids[file_name],
            annotation_label_id=labels[class_name].annotation_label_id,
        )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = selection_tools.run_selection(
        context,
        RunSelectionArgs(
            n_samples=2,
            tag_name="balanced",
            strategies=[AnnotationClassBalancingStrategy(target_distribution="uniform")],
        ),
    )

    assert result["achieved_distributions"] == {
        "annotation_classes": {
            "target": "uniform",
            "values": [
                {"value": "bus", "count": 1, "share": 0.5},
                {"value": "car", "count": 1, "share": 0.5},
            ],
        }
    }


def test_run_selection__strategies_from_json(db_session: Session) -> None:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    context = helpers_agent.create_context(
        session=db_session, collection=collection, selected_sample_ids=[ids["a.jpg"], ids["c.jpg"]]
    )
    # The model sends the strategies as JSON, discriminated by `strategy_name`.
    args = RunSelectionArgs.model_validate_json(
        '{"n_samples": 1, "tag_name": "one", "source": "selection",'
        ' "strategies": [{"strategy_name": "diversity"}]}'
    )

    result = selection_tools.run_selection(context, args)

    assert result["selected_count"] == 1
    tag = tag_resolver.get_by_name(
        session=db_session, tag_name="one", collection_id=collection.collection_id
    )
    assert tag is not None
    selected = tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)
    assert selected[0] in {ids["a.jpg"], ids["c.jpg"]}


def test_run_selection__tag_exists(db_session: Session) -> None:
    collection, _ = helpers_agent.create_collection_with_embeddings(
        session=db_session, embeddings_by_file=_EMBEDDINGS
    )
    helpers_resolvers.create_tag(
        session=db_session, collection_id=collection.collection_id, tag_name="diverse"
    )
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="diverse"):
        selection_tools.run_selection(
            context,
            RunSelectionArgs(
                n_samples=2, tag_name="diverse", strategies=[EmbeddingDiversityStrategy()]
            ),
        )
