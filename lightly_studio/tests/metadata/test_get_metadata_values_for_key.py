"""Tests for the single-key metadata values resolver."""

import pytest
from sqlmodel import Session

import lightly_studio.resolvers.metadata_resolver.sample as metadata_resolver
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


def test_get_metadata_values_for_key__filters_by_sample_ids(
    db_session: Session,
) -> None:
    """When sample_ids is given, only those samples' values are returned."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    samples = [
        create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample{i}.png",
        ).sample
        for i in range(3)
    ]
    for i, sample in enumerate(samples):
        sample["speed"] = float(i)

    result, metadata_type = metadata_resolver.get_metadata_values_for_key(
        session=db_session,
        collection_id=collection_id,
        key="speed",
        sample_ids=[samples[0].sample_id, samples[2].sample_id],
    )

    assert metadata_type == "float"
    assert result == {samples[0].sample_id: 0.0, samples[2].sample_id: 2.0}


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


def test_get_metadata_values_for_key__omits_null_value(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    sample["nullable"] = None

    result, metadata_type = metadata_resolver.get_metadata_values_for_key(
        session=db_session,
        collection_id=collection.collection_id,
        key="nullable",
    )

    assert result == {}
    assert metadata_type == "null"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("enabled", True),
        ("count", 42),
        ("score", 1.5),
        ("items", [1, "two"]),
        ("details", {"nested": "value"}),
        ("key.with.dots", "literal key"),
    ],
)
def test_get_metadata_values_for_key__preserves_value_types_and_literal_keys(
    db_session: Session,
    key: str,
    value: object,
) -> None:
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    sample[key] = value

    result, _ = metadata_resolver.get_metadata_values_for_key(
        session=db_session,
        collection_id=collection.collection_id,
        key=key,
    )

    assert result == {sample.sample_id: value}


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
