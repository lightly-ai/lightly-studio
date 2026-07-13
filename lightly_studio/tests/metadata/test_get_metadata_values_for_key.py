"""Tests for the single-key metadata values resolver."""

import pytest
from sqlmodel import Session

import lightly_studio.resolvers.metadata_resolver.sample as metadata_resolver
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_get_metadata_values_for_key__returns_values_for_requested_key(
    db_session: Session,
) -> None:
    """Return values only for the requested key and its schema type."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    sample1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    ).sample
    sample3 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample3.png",
    ).sample

    sample1["location"] = "city"
    sample1["temperature"] = 25.5
    sample2["location"] = "mountain"
    sample3["is_processed"] = True

    result, metadata_type = metadata_resolver.get_metadata_values_for_key(
        session=db_session,
        collection_id=collection_id,
        key="location",
    )

    assert metadata_type == "string"
    assert result == {
        sample1.sample_id: "city",
        sample2.sample_id: "mountain",
    }


def test_get_metadata_values_for_key__returns_native_values_per_type(
    db_session: Session,
) -> None:
    """Values round-trip to their native Python type for every schema type.

    This runs against whichever dialect the suite targets (DuckDB by default,
    PostgreSQL under ``--postgres``), guarding the dialect-dependent JSON
    decoding: strings, booleans, integers, floats and the gps ``dict`` must all
    come back as native Python values, identically on both backends.
    """
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    sample = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    sample["location"] = "sunny"
    sample["is_processed"] = True
    sample["count"] = 3
    sample["temperature"] = 25.5
    sample["gps"] = GPSCoordinate(lat=1.5, lon=2.5)

    expectations = {
        "location": ("string", "sunny"),
        "is_processed": ("boolean", True),
        "count": ("integer", 3),
        "temperature": ("float", 25.5),
        "gps": ("gps_coordinate", {"lat": 1.5, "lon": 2.5}),
    }
    for key, (expected_type, expected_value) in expectations.items():
        result, metadata_type = metadata_resolver.get_metadata_values_for_key(
            session=db_session,
            collection_id=collection_id,
            key=key,
        )
        assert metadata_type == expected_type, key
        assert result == {sample.sample_id: expected_value}, key
        value = result[sample.sample_id]
        # Guard against booleans arriving as ints (or ints as bools) and numeric
        # values arriving as text strings from a text-returning JSON accessor.
        assert type(value) is type(expected_value), key


def test_get_metadata_values_for_key__missing_key(
    db_session: Session,
) -> None:
    """Return an empty mapping and no type when the key is missing."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    sample = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample["location"] = "city"

    result, metadata_type = metadata_resolver.get_metadata_values_for_key(
        session=db_session,
        collection_id=collection_id,
        key="unknown_key",
    )

    assert result == {}
    assert metadata_type is None


def test_get_metadata_values_for_key__inconsistent_schema_types(
    db_session: Session,
) -> None:
    """Raise if the same metadata key has different schema types."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    sample1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    ).sample

    sample1["location"] = "city"
    sample2["location"] = False

    with pytest.raises(
        ValueError,
        match=r"Metadata field 'location': value does not match schema type 'string'\.",
    ):
        metadata_resolver.get_metadata_values_for_key(
            session=db_session,
            collection_id=collection_id,
            key="location",
        )
