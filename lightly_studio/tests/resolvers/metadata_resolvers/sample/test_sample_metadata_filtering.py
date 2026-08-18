"""Test metadata resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.metadata_resolver.metadata_filter import (
    Metadata,
    MetadataFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_metadata_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create samples
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

    # Add metadata
    sample1["temperature"] = 25
    sample1["location"] = "city"
    sample2["temperature"] = 15
    sample2["location"] = "desert"

    normal_filter = [Metadata("temperature") > 15]
    sample_filter = SampleFilter(metadata_filters=normal_filter)
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection_id, filters=sample_filter
    ).samples
    assert len(samples) == 1
    assert samples[0].sample_id == sample1.sample_id

    # Add a dictionary to metadata
    test_dict = {
        "int_key": 42,
        "nested_list": [1, 2, 3],
    }
    sample1["test_dict"] = test_dict

    sample_filter = SampleFilter(metadata_filters=[Metadata("test_dict.int_key") == 42])
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection_id, filters=sample_filter
    ).samples
    assert len(samples) == 1
    assert samples[0]["test_dict"]["int_key"] == 42

    sample_filter = SampleFilter(metadata_filters=[Metadata("test_dict.nested_list[0]") == 1])
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection_id, filters=sample_filter
    ).samples
    assert len(samples) == 1
    assert samples[0]["test_dict"]["nested_list"][0] == 1


def test_metadata_multiple_filters(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create samples
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
    # Add metadata
    sample1["temperature"] = 25
    sample1["location"] = "desert"
    sample2["temperature"] = 15
    sample2["location"] = "desert"
    test_dict = {
        "string_key": "string_value",
        "int_key": 42,
        "float_key": 3.14,
        "bool_key": True,
        "nested_dict": {"nested_key": "nested_value"},
        "nested_list": [1, 2, 3],
    }
    sample2["test_dict"] = test_dict

    sample_filter = SampleFilter(
        metadata_filters=[
            Metadata("location") == "desert",
            Metadata("test_dict.int_key") == 42,
        ]
    )
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection_id, filters=sample_filter
    ).samples
    assert len(samples) == 1
    assert samples[0].sample_id == sample2.sample_id


def test_metadata_in_filter__concrete_values_and_other_keys(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    first = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/first.png",
    ).sample
    second = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/second.png",
    ).sample
    third = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/third.png",
    ).sample
    first["city"] = "Zurich"
    first["reviewed"] = True
    second["city"] = "Berlin"
    second["reviewed"] = False
    third["city"] = "Paris"
    third["reviewed"] = True

    filters = SampleFilter(
        metadata_filters=[
            MetadataFilter(key="city", op="in", value=["Zurich", "Berlin"]),
            MetadataFilter(key="reviewed", op="in", value=[True]),
        ]
    )
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    assert [sample.sample_id for sample in samples] == [first.sample_id]


@pytest.mark.parametrize("wanted", [True, False])
def test_metadata_filter__boolean_equality(db_session: Session, wanted: bool) -> None:
    """A boolean compares as text, because both databases read it back as text.

    Python calls a bool an int, so the numeric branch would cast "true" to a float
    and the database would raise.
    """
    collection = create_collection(session=db_session)
    reviewed = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/reviewed.png",
    ).sample
    pending = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/pending.png",
    ).sample
    reviewed["reviewed"] = True
    pending["reviewed"] = False

    filters = SampleFilter(metadata_filters=[Metadata("reviewed") == wanted])
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    expected = reviewed if wanted else pending
    assert [sample.sample_id for sample in samples] == [expected.sample_id]


@pytest.mark.parametrize("unwanted", [True, False])
def test_metadata_filter__boolean_inequality(db_session: Session, unwanted: bool) -> None:
    """``!=`` on a boolean compares as text too."""
    collection = create_collection(session=db_session)
    reviewed = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/reviewed.png",
    ).sample
    pending = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/pending.png",
    ).sample
    reviewed["reviewed"] = True
    pending["reviewed"] = False

    filters = SampleFilter(metadata_filters=[Metadata("reviewed") != unwanted])
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    expected = pending if unwanted else reviewed
    assert [sample.sample_id for sample in samples] == [expected.sample_id]


def test_metadata_in_filter__missing(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    concrete = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/concrete.png",
    ).sample
    other_metadata = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/other-metadata.png",
    ).sample
    no_metadata = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/no-metadata.png",
    ).sample
    concrete["city"] = "Zurich"
    other_metadata["country"] = "CH"

    filters = SampleFilter(metadata_filters=[MetadataFilter(key="city", op="in", value=[None])])
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    assert {sample.sample_id for sample in samples} == {
        other_metadata.sample_id,
        no_metadata.sample_id,
    }


@pytest.mark.parametrize(("index", "expected_value"), [(-1, 3), (-3, 1)])
def test_metadata_filter__negative_index(
    db_session: Session, index: int, expected_value: int
) -> None:
    """A negative index counts from the end of the array."""
    collection = create_collection(session=db_session)
    matching = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/matching.png",
    ).sample
    excluded = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/excluded.png",
    ).sample
    matching["test_dict"] = {"nested_list": [1, 2, 3]}
    excluded["test_dict"] = {"nested_list": [9, 9, 9]}

    filters = SampleFilter(
        metadata_filters=[Metadata(f"test_dict.nested_list[{index}]") == expected_value]
    )
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    assert [sample.sample_id for sample in samples] == [matching.sample_id]


@pytest.mark.parametrize(
    "payload",
    [
        # Closes the string literal and starts a new statement.
        "x'); DROP TABLE victim; --",
        # Closes the DuckDB json_extract call and appends a subquery.
        "x') AS FLOAT), (SELECT 1 FROM victim) --",
        # Turns the comparison into a tautology.
        "temp' OR '1'='1",
        # Rides in through the array-index brackets, which once rendered unquoted.
        "a[0; DROP TABLE victim]",
        # Reads as JSONPath rather than as a key name.
        "$.temp",
        # Concatenates a subquery into the value.
        "'||(SELECT count(*) FROM victim)||'",
    ],
)
def test_metadata_filter__injection_payload_is_inert(db_session: Session, payload: str) -> None:
    """A payload key runs as a lookup that finds nothing and leaves the data alone."""
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    sample["temp"] = 25

    payload_filter = SampleFilter(metadata_filters=[Metadata(payload) == 25])
    matched = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=payload_filter
    ).samples

    assert matched == []

    # The sample and its metadata survived, so nothing the payload carried ran.
    intact_filter = SampleFilter(metadata_filters=[Metadata("temp") == 25])
    still_there = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=intact_filter
    ).samples

    assert [found.sample_id for found in still_there] == [sample.sample_id]


@pytest.mark.parametrize("key", ["$", "$.temp", "$x", "/temp", "/"])
def test_metadata_filter__path_syntax_key_is_a_key(db_session: Session, key: str) -> None:
    """DuckDB reads these as paths unless they are bound as pointers.

    Without that, `$.temp` reads the `temp` field of the same document and matches,
    and `$x` raises. Neither database has a `key` field here, so nothing matches.
    """
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    sample["temp"] = 25

    filters = SampleFilter(metadata_filters=[Metadata(key) == 25])
    matched = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    assert matched == []


def test_metadata_filter__key_with_quote(db_session: Session) -> None:
    """A quote in the key is bound, not compiled into the statement."""
    collection = create_collection(session=db_session)
    matching = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/matching.png",
    ).sample
    excluded = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/excluded.png",
    ).sample
    matching["temp're"] = 25
    excluded["temp're"] = 15

    filters = SampleFilter(metadata_filters=[Metadata("temp're") > 20])
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    assert [sample.sample_id for sample in samples] == [matching.sample_id]


def test_metadata_in_filter__concrete_and_missing_special_key(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    concrete = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/concrete.png",
    ).sample
    missing = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/missing.png",
    ).sample
    excluded = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/excluded.png",
    ).sample
    concrete["city.name's"] = "Zurich"
    excluded["city.name's"] = "Paris"

    filters = SampleFilter(
        metadata_filters=[MetadataFilter(key="city.name's", op="in", value=["Zurich", None])]
    )
    samples = sample_resolver.get_filtered_samples(
        session=db_session, collection_id=collection.collection_id, filters=filters
    ).samples

    assert {sample.sample_id for sample in samples} == {
        concrete.sample_id,
        missing.sample_id,
    }
