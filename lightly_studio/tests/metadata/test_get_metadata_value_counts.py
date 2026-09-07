"""Tests for categorical metadata value counts."""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy
from sqlmodel import Session

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.metadata_resolver.sample import categorical_value_counts
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import create_collection, create_image


@contextlib.contextmanager
def _count_queries(session: Session) -> Generator[list[str], None, None]:
    """Context manager that records all SQL statements executed on the session."""
    executed: list[str] = []

    def _before_execute(
        _conn: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: Any
    ) -> None:
        executed.append(statement)

    bind = session.get_bind()
    sqlalchemy.event.listen(bind, "before_cursor_execute", _before_execute)
    try:
        yield executed
    finally:
        sqlalchemy.event.remove(bind, "before_cursor_execute", _before_execute)


def test_get_metadata_value_counts__categorical_values_and_missing(
    db_session: Session,
) -> None:
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

    assert set(counts) == {"city", "active"}
    assert [(entry.value, entry.count) for entry in counts["city"].value_counts] == [
        ("Zurich", 2),
        ("", 1),
        ("Missing", 1),
        ("Other", 1),
        ("__missing__", 2),
    ]
    assert [(entry.value, entry.count) for entry in counts["active"].value_counts] == [
        (True, 3),
        (False, 2),
        ("__missing__", 2),
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

    assert len(counts.value_counts) == 21
    assert (counts.value_counts[0].value, counts.value_counts[0].count) == ("value-20", 2)
    assert [entry.value for entry in counts.value_counts[1:20]] == [
        f"value-{index:02d}" for index in range(19)
    ]
    assert (counts.value_counts[20].value, counts.value_counts[20].count) == ("__other__", 1)


def test_get_metadata_value_counts__aggregates_sum_to_the_samples_in_scope(
    db_session: Session,
) -> None:
    """The top values plus both aggregates account for every sample in scope."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    for index in range(22):
        _create_sample(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"category": f"value-{index:02d}"},
        )
    _create_explicit_null_sample(db_session=db_session, collection_id=collection_id)
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/no-metadata.png",
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session, collection_id=collection_id
    )["category"]

    by_value = {entry.value: entry.count for entry in counts.value_counts}
    assert by_value["__other__"] == 2
    assert by_value["__missing__"] == 2
    assert sum(entry.count for entry in counts.value_counts) == 24


def test_get_metadata_value_counts__no_aggregates_when_every_value_is_shown(
    db_session: Session,
) -> None:
    """Zero-count aggregates are omitted rather than rendered as empty buckets."""
    collection = create_collection(session=db_session)
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "Zurich"},
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection.collection_id,
        metadata={"city": "Bern"},
    )

    counts = categorical_value_counts.get_metadata_value_counts(
        session=db_session, collection_id=collection.collection_id
    )["city"]

    assert [(entry.value, entry.count) for entry in counts.value_counts] == [
        ("Bern", 1),
        ("Zurich", 1),
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


def test_get_metadata_value_counts__query_count_does_not_grow_with_field_count(
    db_session: Session,
) -> None:
    """DB round-trips must stay constant as the number of categorical fields grows.

    Without active metadata filters all fields are batched into a single unnest
    query plus one total-count query, so the number of statements must not grow
    linearly with the number of fields.
    """
    collection_few = create_collection(session=db_session)
    collection_many = create_collection(session=db_session)
    few_fields = {f"field_{i}": f"value_{i}" for i in range(3)}
    many_fields = {f"field_{i}": f"value_{i}" for i in range(20)}
    _create_sample(
        db_session=db_session,
        collection_id=collection_few.collection_id,
        metadata=few_fields,
    )
    _create_sample(
        db_session=db_session,
        collection_id=collection_many.collection_id,
        metadata=many_fields,
    )

    with _count_queries(db_session) as few_queries:
        categorical_value_counts.get_metadata_value_counts(
            session=db_session,
            collection_id=collection_few.collection_id,
            fields=list(few_fields),
        )
    with _count_queries(db_session) as many_queries:
        categorical_value_counts.get_metadata_value_counts(
            session=db_session,
            collection_id=collection_many.collection_id,
            fields=list(many_fields),
        )

    assert len(few_queries) == len(many_queries), (
        f"Query count grew from {len(few_queries)} (3 fields) to "
        f"{len(many_queries)} (20 fields) — O(N) queries detected"
    )


def test_get_metadata_value_counts__query_count_with_active_filter(
    db_session: Session,
) -> None:
    """With one active metadata filter the query count is bounded by the filter count.

    The filtered field gets its own query (its filter must be excluded); all other
    fields are still batched together. So the total must be much less than N*2.
    """
    collection = create_collection(session=db_session)
    fields = {f"field_{i}": f"value_{i}" for i in range(10)}
    _create_sample(db_session=db_session, collection_id=collection.collection_id, metadata=fields)

    filters = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[MetadataFilter(key="field_0", op="==", value="value_0")]
        )
    )
    with _count_queries(db_session) as queries:
        categorical_value_counts.get_metadata_value_counts(
            session=db_session,
            collection_id=collection.collection_id,
            filters=filters,
            fields=list(fields),
        )

    # Expected: schema lookup + total count + 1 batch for unfiltered fields
    # + 1 query for the filtered field = well under 2*N=20.
    assert len(queries) < len(fields) * 2, (
        f"Query count {len(queries)} is too high for {len(fields)} fields with 1 active filter"
    )


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
