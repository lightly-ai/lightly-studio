"""Tests for categorical metadata value counts."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Session

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.metadata_resolver.sample import categorical_value_counts
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import create_collection, create_image


def test_get_metadata_value_counts__string_values_and_missing(
    db_session: Session,
) -> None:
    """String values, nulls, and missing metadata have separate buckets."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    _create_sample(
        db_session=db_session,
        collection_id=collection_id,
        metadata={"city": "Zurich", "active": True, "score": 1},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection_id,
        metadata={"city": "Zurich", "active": False},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection_id,
        metadata={"city": "", "active": False},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection_id,
        metadata={"city": "Missing", "active": True},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection_id,
        metadata={"city": "Other", "active": True},
    )
    _create_explicit_null_sample(db_session=db_session, collection_id=collection_id)
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/no-metadata.png",
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session, collection_id=collection_id
    )

    assert set(counts) == {"city"}
    assert [(entry.value, entry.count) for entry in counts["city"].value_counts] == [
        ("Zurich", 2),
        ("", 1),
        ("Missing", 1),
        ("Other", 1),
    ]
    assert [(entry.value, entry.count) for entry in counts["active"].value_counts] == [
        (False, 1),
        (True, 1),
    ]


def test_get_metadata_value_counts__top_twenty_and_collection_isolation(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    for index in range(21):
        _create_sample(
            db_session=db_session,
            collection_id=collection.collection_id,
            metadata={"category": f"value-{index:02d}"},
        )
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"category": "value-20"},
    )

    other_collection = create_collection(session=db_session)
    _create_sample(
        db_session=db_session,
        collection_id=other_collection.collection_id,
        metadata={"category": "value-00"},
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session, collection_id=collection.collection_id
    )["category"]

    assert len(counts.value_counts) == 20
    assert (counts.value_counts[0].value, counts.value_counts[0].count) == ("value-20", 2)
    assert [entry.value for entry in counts.value_counts[1:]] == [
        f"value-{index:02d}" for index in range(19)
    ]


def test_get_metadata_value_counts__filters_and_own_key_exclusion(
    db_session: Session,
) -> None:
    """Each field's own metadata filter is dropped while all other filters still AND-apply.

    When counting city values, the city filter is excluded so both A and B are visible;
    the group filter still applies, limiting results to samples in group x (samples 1 and 2).
    When counting group values, the group filter is excluded so both x groups are visible;
    the city filter still applies, limiting results to samples with city A (sample 1 only).
    """
    collection = create_collection(session=db_session)
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "A", "group": "x"},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "B", "group": "x"},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "B", "group": "y"},
    )
    filters = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[
                MetadataFilter(key="city", op="==", value="A"),
                MetadataFilter(key="group", op="==", value="x"),
            ]
        )
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session,
        collection_id=collection.collection_id,
        filters=filters,
    )

    assert [(entry.value, entry.count) for entry in counts["city"].value_counts] == [
        ("A", 1),
        ("B", 1),
    ]
    assert [(entry.value, entry.count) for entry in counts["group"].value_counts] == [("x", 1)]


def test_get_metadata_value_counts__fields_limits_counted_keys(
    db_session: Session,
) -> None:
    """Only fields listed in the fields argument are counted."""
    collection = create_collection(session=db_session)
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "Zurich", "group": "x", "active": True},
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session,
        collection_id=collection.collection_id,
        fields=["city"],
    )

    assert set(counts) == {"city"}
    assert counts["city"].value_counts[0].value == "Zurich"


def test_get_metadata_value_counts__known_fields_with_no_matches(
    db_session: Session,
) -> None:
    """Fields known from the collection schema appear even when all samples are filtered out.

    The schema is built from all samples regardless of filters, so known fields
    appear in the result with empty counts rather than being absent.
    """
    collection = create_collection(session=db_session)
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "A"},
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session,
        collection_id=collection.collection_id,
        filters=ImageFilter(width=FilterDimensions(min=10_000)),
    )

    assert counts["city"].value_counts == []


def test_get_metadata_value_counts__unknown_collection_is_empty(db_session: Session) -> None:
    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session, collection_id=uuid4()
    )
    assert counts == {}


def test_get_metadata_value_counts__literal_top_level_keys(db_session: Session) -> None:
    """Keys with dots or apostrophes are treated as literal field names, not path expressions."""
    collection = create_collection(session=db_session)
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"site.name": "Zurich", "owner's site": "primary"},
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session, collection_id=collection.collection_id
    )

    assert counts["site.name"].value_counts[0].value == "Zurich"
    assert counts["owner's site"].value_counts[0].value == "primary"


def _create_sample(
    db_session: Session,
    collection_id: UUID,
    metadata: dict[str, Any],
) -> None:
    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs=f"/path/to/{uuid4()}.png",
    )
    for key, value in metadata.items():
        image.sample[key] = value


def _create_explicit_null_sample(db_session: Session, collection_id: UUID) -> None:
    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/explicit-null.png",
    )
    db_session.add(
        SampleMetadataTable(
            sample_id=image.sample_id,
            data={"city": None},
            metadata_schema={"city": "string"},
        )
    )
    db_session.commit()
