from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.core.sample import Sample
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_dataset, create_sample, create_tag


class TestSample:
    def test_basic_fields_get(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/sample1.png",
            width=640,
            height=480,
        )
        sample = Sample(inner=image_table)

        # Test "get".
        assert sample.file_name == "sample1.png"
        assert sample.width == 640
        assert sample.height == 480
        assert sample.dataset_id == dataset.dataset_id
        assert sample.file_path_abs == "/path/to/sample1.png"
        assert sample.sample_id == image_table.sample_id
        assert sample.created_at == image_table.created_at
        assert sample.updated_at == image_table.updated_at

    def test_basic_fields_set(self, mocker: MockerFixture, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
        )
        sample = Sample(inner=image_table)

        # Spy on commit.
        spy_commit = mocker.spy(test_db, "commit")

        # Test "set".
        sample.file_name = "sample1.png"
        assert spy_commit.call_count == 1
        sample.width = 1000
        assert spy_commit.call_count == 2

        new_image_table = sample_resolver.get_by_id(
            session=test_db,
            dataset_id=dataset.dataset_id,
            sample_id=sample.sample_id,
        )
        assert new_image_table is not None
        assert new_image_table.file_name == "sample1.png"
        assert new_image_table.width == 1000

        # Can't set a foreign key to a non-existent id.
        with pytest.raises(IntegrityError):
            sample.dataset_id = UUID(int=123456)

    def test_add_tag(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
        )
        sample = Sample(inner=image_table)

        # Test adding a tag.
        assert [tag.name for tag in sample.inner.tags] == []
        sample.add_tag("tag1")
        assert [tag.name for tag in sample.inner.tags] == ["tag1"]
        sample.add_tag("tag2")
        assert sorted([tag.name for tag in sample.inner.tags]) == ["tag1", "tag2"]
        sample.add_tag("tag1")
        assert sorted([tag.name for tag in sample.inner.tags]) == ["tag1", "tag2"]

    def test_remove_tag(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
        )
        sample = Sample(inner=image_table)

        # Add some tags first
        sample.add_tag("tag1")
        sample.add_tag("tag2")
        assert sorted([tag.name for tag in sample.inner.tags]) == ["tag1", "tag2"]

        # Test removing an existing, associated tag
        sample.remove_tag("tag1")
        assert [tag.name for tag in sample.inner.tags] == ["tag2"]

        # Test removing a non-existent tag (should not error)
        sample.remove_tag("nonexistent")
        assert [tag.name for tag in sample.inner.tags] == ["tag2"]

        # Test removing a tag that exists in database but isn't associated with sample
        create_tag(session=test_db, dataset_id=dataset.dataset_id, tag_name="unassociated")
        sample.remove_tag("unassociated")
        assert [tag.name for tag in sample.inner.tags] == ["tag2"]

        # Remove the last tag
        sample.remove_tag("tag2")
        assert [tag.name for tag in sample.inner.tags] == []

    def test_tags_property_get(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
        )
        sample = Sample(inner=image_table)

        # Test empty tags
        assert sample.tags == set()

        # Test with tags
        sample.add_tag("tag1")
        sample.add_tag("tag2")
        assert sample.tags == {"tag1", "tag2"}

    def test_tags_property_set(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
        )
        sample = Sample(inner=image_table)

        # Test setting tags from empty to multiple
        sample.tags = {"tag1", "tag2", "tag3"}
        assert sample.tags == {"tag1", "tag2", "tag3"}
        assert sorted([tag.name for tag in sample.inner.tags]) == ["tag1", "tag2", "tag3"]

        # Test replacing existing tags with new ones
        sample.tags = {"tag2", "tag4", "tag5"}
        assert sample.tags == {"tag2", "tag4", "tag5"}
        assert sorted([tag.name for tag in sample.inner.tags]) == ["tag2", "tag4", "tag5"]

        # Test clearing all tags
        sample.tags = set()
        assert sample.tags == set()
        assert [tag.name for tag in sample.inner.tags] == []

    def test_metadata(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
        )
        sample = Sample(inner=image_table)

        # Test getting from empty metadata
        assert sample.metadata["nonexistent"] is None

        # Test setting metadata on a sample with no existing metadata
        sample.metadata["string_key"] = "string_value"
        sample.metadata["int_key"] = 123
        sample.metadata["float_key"] = 45.67
        sample.metadata["bool_key"] = True
        sample.metadata["list_key"] = [1, 2, 3]
        sample.metadata["dict_key"] = {"nested": "value"}

        # Verify all values were set correctly
        assert sample.metadata["string_key"] == "string_value"
        assert sample.metadata["int_key"] == 123
        assert sample.metadata["float_key"] == 45.67
        assert sample.metadata["bool_key"] is True
        assert sample.metadata["list_key"] == [1, 2, 3]
        assert sample.metadata["dict_key"] == {"nested": "value"}

        # Test overwriting existing metadata values
        sample.metadata["string_key"] = "updated_value"
        assert sample.metadata["string_key"] == "updated_value"

    def test_metadata__schema_must_match(self, test_db: Session) -> None:
        dataset = create_dataset(session=test_db)
        image_table1 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/sample1.png",
        )
        image_table2 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/sample2.png",
        )
        sample1 = Sample(inner=image_table1)
        sample2 = Sample(inner=image_table2)

        # Set the initial value to a string
        sample1.metadata["key"] = "string_value"

        # Test setting the value to a different type fails
        with pytest.raises(ValueError, match="Expected string, got integer"):
            sample1.metadata["key"] = 123

        # For a different sample, the same schema check does not apply
        # TODO(Michal, 9/2025): But shouldn't it?
        sample2.metadata["key"] = 123
