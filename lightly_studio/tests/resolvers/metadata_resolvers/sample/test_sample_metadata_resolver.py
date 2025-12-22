"""Test metadata resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import (
    metadata_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_metadata(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    # Create samples.
    sample = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    metadata_resolver.set_value_for_sample(
        session=test_db,
        sample_id=sample.sample_id,
        key="str_value",
        value="value1",
    )
    metadata_resolver.set_value_for_sample(
        session=test_db,
        sample_id=sample.sample_id,
        key="int_value",
        value=1,
    )
    # Check metadata is set correctly.
    assert sample["str_value"] == "value1"
    assert sample["int_value"] == 1
    assert (
        metadata_resolver.get_value_for_sample(
            session=test_db, sample_id=sample.sample_id, key="str_value"
        )
        == "value1"
    )
    assert (
        metadata_resolver.get_value_for_sample(
            session=test_db, sample_id=sample.sample_id, key="int_value"
        )
        == 1
    )

    # Test adding a list to metadata
    test_list = [1, 2, 3, "four", 5.5]
    sample["test_list"] = test_list

    # Verify the list was stored correctly
    retrieved_list = sample["test_list"]
    assert retrieved_list == test_list
    assert isinstance(retrieved_list, list)
    assert len(retrieved_list) == 5
    assert retrieved_list[0] == 1
    assert retrieved_list[3] == "four"

    # Test adding a dictionary to metadata
    test_dict = {
        "string_key": "string_value",
        "int_key": 42,
        "float_key": 3.14,
        "bool_key": True,
        "nested_dict": {"nested_key": "nested_value"},
        "nested_list": [1, 2, 3],
    }
    sample["test_dict"] = test_dict
    # Verify the dictionary was stored correctly
    retrieved_dict = sample["test_dict"]
    assert retrieved_dict == test_dict
    assert isinstance(retrieved_dict, dict)
    assert retrieved_dict["string_key"] == "string_value"
    assert retrieved_dict["int_key"] == 42
    assert retrieved_dict["float_key"] == 3.14
    assert retrieved_dict["bool_key"] is True
    assert retrieved_dict["nested_dict"]["nested_key"] == "nested_value"
    assert retrieved_dict["nested_list"] == [1, 2, 3]


def test_metadata__update_type(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    # Create samples.
    sample = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample["count"] = 42  # Creates INTEGER type
    metadata_resolver.set_value_for_sample(
        session=test_db,
        sample_id=sample.sample_id,
        key="name",
        value="test",
    )
    # Check metadata is set correctly.
    assert sample["name"] == "test"

    # Try to set a value of a different type.
    with pytest.raises(
        ValueError,
        match="Value type mismatch for key 'name'. Expected string, got integer",
    ):
        sample["name"] = 12

    with pytest.raises(
        ValueError,
        match="Value type mismatch for key 'count'. Expected integer, got string",
    ):
        sample["count"] = "42"


def test_metadata_get_value_for_missing_key(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    # Create samples.
    sample = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    # Check with empty metadata dict.
    assert sample["missing_key"] is None
    # Add some metadata and check again the missing key.
    sample["some_key"] = "some_value"
    assert sample["some_key"] == "some_value"
    assert sample["missing_key"] is None
