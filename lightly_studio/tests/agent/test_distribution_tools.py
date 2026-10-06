from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.agent import distribution_tools
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.distribution_tools import GetDistributionArgs
from lightly_studio.resolvers import metadata_resolver, tag_resolver
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from tests import helpers_resolvers
from tests.agent import helpers_agent

_EMBEDDINGS = {
    "a.jpg": [1.0, 0.0],
    "b.jpg": [0.9, 0.1],
    "c.jpg": [0.0, 1.0],
    "d.jpg": [0.1, 0.9],
}

# The metadata of each image. "d.jpg" has no weather, no speed and no date.
_WEATHER = {"a.jpg": "rain", "b.jpg": "rain", "c.jpg": "sun"}
_IS_NIGHT = {"a.jpg": True, "b.jpg": False, "c.jpg": False, "d.jpg": False}
_SPEED = {"a.jpg": 0.0, "b.jpg": 1.0, "c.jpg": 10.0}
_DATE = {"a.jpg": "2025-06-01", "b.jpg": "2025-07-01T10:00:00", "c.jpg": "n/a"}
_METADATA: dict[str, dict[str, Any]] = {
    "weather": _WEATHER,
    "is_night": _IS_NIGHT,
    "speed": _SPEED,
    "date": _DATE,
}

# The annotation classes on each image. "d.jpg" has none.
_CLASSES = {"a.jpg": ["car"], "b.jpg": ["car", "car", "bus"], "c.jpg": ["car"]}


def test_get_distribution__categorical(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    result = distribution_tools.get_distribution(
        context, GetDistributionArgs(metadata_keys=["weather", "is_night"])
    )

    assert result == {
        "sample_count": 4,
        "metadata": {
            "weather": [
                {"value": "rain", "count": 2, "share": 0.5},
                {"value": "sun", "count": 1, "share": 0.25},
                {"value": "__missing__", "count": 1, "share": 0.25},
            ],
            "is_night": [
                {"value": False, "count": 3, "share": 0.75},
                {"value": True, "count": 1, "share": 0.25},
            ],
        },
    }


def test_get_distribution__numeric(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    result = distribution_tools.get_distribution(
        context, GetDistributionArgs(metadata_keys=["speed"])
    )

    # Ten bins of width 1 from 0.0 to 10.0, and the sample without a speed.
    speed = result["metadata"]["speed"]
    assert [entry["count"] for entry in speed] == [1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1]
    assert speed[0] == {"min": 0.0, "max": 1.0, "count": 1, "share": 0.25}
    assert speed[9] == {"min": 9.0, "max": 10.0, "count": 1, "share": 0.25}
    assert speed[10] == {"value": "__missing__", "count": 1, "share": 0.25}


def test_get_distribution__years(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    result = distribution_tools.get_distribution(context, GetDistributionArgs(year_keys=["date"]))

    assert result == {
        "sample_count": 4,
        "years": {
            "date": [
                {"value": "2025", "count": 2, "share": 0.5},
                {"value": "__other__", "count": 1, "share": 0.25},
                {"value": "__missing__", "count": 1, "share": 0.25},
            ],
        },
    }


def test_get_distribution__annotation_classes_of_tag(db_session: Session) -> None:
    context, ids = _create_context(session=db_session)
    tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=context.collection.collection_id, tag_name="picked"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[ids["b.jpg"], ids["c.jpg"]]
    )
    # The model sends the arguments as JSON.
    args = GetDistributionArgs.model_validate_json(
        '{"annotation_classes": true, "source": "tag:picked"}'
    )

    result = distribution_tools.get_distribution(context, args)

    assert result == {
        "sample_count": 2,
        "annotation_classes": [
            {"value": "car", "count": 2, "share": 1.0},
            {"value": "bus", "count": 1, "share": 0.5},
        ],
    }


def test_get_distribution__nothing_to_count(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match="at least one"):
        distribution_tools.get_distribution(context, GetDistributionArgs())


@pytest.mark.parametrize("year_key", ["season", "speed"])
def test_get_distribution__year_key_not_string(db_session: Session, year_key: str) -> None:
    context, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match=f"'{year_key}' is not a string metadata key"):
        distribution_tools.get_distribution(context, GetDistributionArgs(year_keys=[year_key]))


def test_get_metadata_distributions__unknown_key(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match=r"not string, boolean or numeric .*\['season'\]"):
        distribution_tools.get_metadata_distributions(
            context=context, sample_ids=None, keys=["weather", "season"]
        )


def test_get_annotation_class_distribution__objects(db_session: Session) -> None:
    context, _ = _create_context(session=db_session)

    entries = distribution_tools.get_annotation_class_distribution(
        context=context, sample_ids=None, count_mode=AnnotationCountMode.OBJECTS
    )

    # Four car annotations and one bus annotation.
    assert entries == [
        {"value": "car", "count": 4, "share": 0.8},
        {"value": "bus", "count": 1, "share": 0.2},
    ]


def _create_context(session: Session) -> tuple[AgentContext, dict[str, UUID]]:
    """Create a collection with the metadata and the annotation classes of the module."""
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=session, embeddings_by_file=_EMBEDDINGS
    )
    for key, values in _METADATA.items():
        for file_name, value in values.items():
            metadata_resolver.set_value_for_sample(
                session=session, sample_id=ids[file_name], key=key, value=value
            )
    labels = {
        name: helpers_resolvers.create_annotation_label(
            session=session, root_collection_id=collection.collection_id, label_name=name
        )
        for name in ("car", "bus")
    }
    for file_name, class_names in _CLASSES.items():
        for class_name in class_names:
            helpers_resolvers.create_annotation(
                session=session,
                collection_id=collection.collection_id,
                sample_id=ids[file_name],
                annotation_label_id=labels[class_name].annotation_label_id,
            )
    context = helpers_agent.create_context(session=session, collection=collection)
    return context, ids
