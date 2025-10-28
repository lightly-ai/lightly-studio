"""Test metadata resolver."""

from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from lightly_studio.resolvers.metadata_resolver.metadata_filter import (
    Metadata,
)
from lightly_studio.resolvers.samples_filter import SampleFilter
from tests.helpers_resolvers import (
    create_dataset,
    create_sample,
)


def test_metadata_filter(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    sample1 = create_sample(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample2 = create_sample(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    ).sample

    # Add metadata
    sample1["temperature"] = 25
    sample1["location"] = "city"
    sample2["temperature"] = 15
    sample2["location"] = "desert"

    normal_filter = [Metadata("temperature") > 15]
    sample_filter = SampleFilter(metadata_filters=normal_filter)
    images = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, filters=sample_filter
    ).samples
    samples = [image.sample for image in images]
    assert len(samples) == 1
    assert samples[0].sample_id == sample1.sample_id

    # Add a dictionary to metadata
    test_dict = {
        "int_key": 42,
        "nested_list": [1, 2, 3],
    }
    sample1["test_dict"] = test_dict

    sample_filter = SampleFilter(metadata_filters=[Metadata("test_dict.int_key") == 42])
    images = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, filters=sample_filter
    ).samples
    samples = [image.sample for image in images]
    assert len(samples) == 1
    assert samples[0]["test_dict"]["int_key"] == 42

    sample_filter = SampleFilter(metadata_filters=[Metadata("test_dict.nested_list[0]") == 1])
    images = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, filters=sample_filter
    ).samples
    samples = [image.sample for image in images]
    assert len(samples) == 1
    assert samples[0]["test_dict"]["nested_list"][0] == 1


def test_metadata_multiple_filters(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    sample1 = create_sample(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    ).sample
    sample2 = create_sample(
        session=test_db,
        dataset_id=dataset_id,
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
    images = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, filters=sample_filter
    ).samples
    samples = [image.sample for image in images]
    assert len(samples) == 1
    assert samples[0].sample_id == sample2.sample_id
