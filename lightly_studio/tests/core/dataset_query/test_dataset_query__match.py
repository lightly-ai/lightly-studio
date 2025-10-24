from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_dataset, create_sample, create_tag


class TestDatasetQueryMatch:
    def test_match__width_less_than(self, test_db: Session) -> None:
        """Test filtering samples with width less than 600."""
        # Arrange
        dataset = create_dataset(session=test_db)
        sample1 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/small.jpg",
            width=500,
            height=400,
        )
        create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/large.jpg",
            width=800,
            height=600,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(SampleField.width < 600).to_list()

        # Assert
        assert len(result_samples) == 1
        assert result_samples[0].sample_id == sample1.sample_id

    def test_match__file_name_equals(self, test_db: Session) -> None:
        """Test filtering samples by file name equal to 'target.jpg'."""
        # Arrange
        dataset = create_dataset(session=test_db)
        sample1 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/target.jpg",
            width=100,
            height=100,
        )
        create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/other.jpg",
            width=200,
            height=200,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(SampleField.file_name == "target.jpg").to_list()

        # Assert
        assert len(result_samples) == 1
        assert result_samples[0].sample_id == sample1.sample_id

    def test_match__created_at_newer(self, test_db: Session) -> None:
        """Test filtering samples by created_at field newer than a specific datetime."""
        # Arrange
        dataset = create_dataset(session=test_db)
        cutoff_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Create older sample
        older_sample = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/old.jpg",
            width=100,
            height=100,
        )
        # Update created_at to be older
        older_sample.created_at = datetime(2023, 12, 31, 10, 0, 0, tzinfo=timezone.utc)
        test_db.add(older_sample)
        test_db.commit()
        test_db.refresh(older_sample)

        # Create newer sample
        newer_sample = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/new.jpg",
            width=200,
            height=200,
        )
        # Update created_at to be newer
        newer_sample.created_at = datetime(2024, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        test_db.add(newer_sample)
        test_db.commit()
        test_db.refresh(newer_sample)

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(SampleField.created_at > cutoff_time).to_list()

        # Assert
        assert len(result_samples) == 1
        assert result_samples[0].sample_id == newer_sample.sample_id

    def test_match__boolean_combo_flat(self, test_db: Session) -> None:
        """Test filtering samples with a flat boolean combination."""
        dataset = create_dataset(session=test_db)
        create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/target.jpg",
            height=10,
        )
        sample2 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/other.jpg",
            height=11,
        )

        create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/more.jpg",
            height=20,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(
            AND(SampleField.height < 20, SampleField.height > 10)
        ).to_list()

        # Assert
        assert len(result_samples) == 1
        assert result_samples[0].sample_id == sample2.sample_id

    def test_match__boolean_combo_nested(self, test_db: Session) -> None:
        """Test filtering samples with a nested boolean combination."""
        dataset = create_dataset(session=test_db)
        create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/target.jpg",
            height=10,
        )
        sample2 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/other.jpg",
            height=11,
        )

        sample3 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/more.jpg",
            height=20,
        )

        sample4 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/more_2.jpg",
            height=1,
        )

        sample5 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/more_3.jpg",
            height=50,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(
            OR(
                SampleField.file_name == "more.jpg",  # sample3
                AND(  # sample2
                    SampleField.height < 20, SampleField.height > 10
                ),
                NOT(  # sample4 & sample 5
                    AND(SampleField.height > 2, SampleField.height < 49),
                ),
            )
        ).to_list()

        sample_ids_in_result = {sample.sample_id for sample in result_samples}

        # Assert
        assert len(result_samples) == 4
        assert sample2.sample_id in sample_ids_in_result
        assert sample3.sample_id in sample_ids_in_result
        assert sample4.sample_id in sample_ids_in_result
        assert sample5.sample_id in sample_ids_in_result

    def test_match__multiple_calls_raises_error(self, test_db: Session) -> None:
        """Test that calling match() twice raises ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.match(SampleField.width < 500)

        # Act & Assert
        with pytest.raises(
            ValueError, match="match\\(\\) can only be called once per DatasetQuery instance"
        ):
            query.match(SampleField.width > 500)

    def test_match__tags_contains(self, test_db: Session) -> None:
        """Test tag contains expression with three samples and two tags."""
        # Arrange
        dataset = create_dataset(session=test_db)
        dataset_id = dataset.dataset_id

        # Create three samples
        _sample1 = create_sample(
            session=test_db, dataset_id=dataset_id, file_path_abs="/path/to/sample1.jpg"
        )  # no tags
        sample2 = create_sample(
            session=test_db, dataset_id=dataset_id, file_path_abs="/path/to/sample2.jpg"
        )  # dog only
        sample3 = create_sample(
            session=test_db, dataset_id=dataset_id, file_path_abs="/path/to/sample3.jpg"
        )  # dog and cat

        # Create two tags
        dog_tag = create_tag(session=test_db, dataset_id=dataset_id, tag_name="dog")
        cat_tag = create_tag(session=test_db, dataset_id=dataset_id, tag_name="cat")

        # Assign tags
        tag_resolver.add_tag_to_sample(
            session=test_db, tag_id=dog_tag.tag_id, sample=sample2.sample
        )
        tag_resolver.add_tag_to_sample(
            session=test_db, tag_id=dog_tag.tag_id, sample=sample3.sample
        )
        tag_resolver.add_tag_to_sample(
            session=test_db, tag_id=cat_tag.tag_id, sample=sample3.sample
        )

        # Test dog tag
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(SampleField.tags.contains("dog")).to_list()
        assert len(result_samples) == 2
        assert {result_samples[0].sample_id, result_samples[1].sample_id} == {
            sample2.sample_id,
            sample3.sample_id,
        }

        # Test cat tag
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.match(SampleField.tags.contains("cat")).to_list()
        assert len(result_samples) == 1
        assert result_samples[0].sample_id == sample3.sample_id
