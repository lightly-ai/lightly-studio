from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.sample_field import SampleField
from tests.helpers_resolvers import create_dataset, create_sample


class TestDatasetQuerySlice:
    def test_slice__basic_parameters(self, test_db: Session) -> None:
        """Test slice method with basic parameters (no DB execution)."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act
        result_query = query.slice(offset=2, limit=3)

        # Assert
        assert result_query is query  # Should return self for chaining
        assert query._slice == slice(2, 5)  # offset=2, limit=3 -> slice(2, 5)

    def test_slice__limit_only(self, test_db: Session) -> None:
        """Test slice with only limit parameter."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act
        query.slice(limit=5)

        # Assert
        assert query._slice == slice(0, 5)  # offset defaults to 0

    def test_slice__offset_only(self, test_db: Session) -> None:
        """Test slice with only offset parameter."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act
        query.slice(offset=3)

        # Assert
        assert query._slice == slice(3, None)  # no limit

    def test_slice__multiple_calls_raises_error(self, test_db: Session) -> None:
        """Test that calling slice() twice raises ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.slice(limit=5)

        # Act & Assert
        with pytest.raises(
            ValueError, match="slice\\(\\) can only be called once per DatasetQuery instance"
        ):
            query.slice(offset=2)

    def test__getitem____slice_variations(self, test_db: Session) -> None:
        """Test various slice notations with database execution."""
        # Arrange
        dataset = create_dataset(session=test_db)
        samples = []
        for i in range(5):
            sample = create_sample(
                session=test_db,
                dataset_id=dataset.dataset_id,
                file_path_abs=f"sample_{i}.jpg",
            )
            samples.append(sample)

        # Test basic slice [start:stop]
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[1:4].to_list()
        expected_sample_ids = [samples[i].sample_id for i in [1, 2, 3]]
        actual_sample_ids = [sample.sample_id for sample in result_samples]
        assert actual_sample_ids == expected_sample_ids

        # Test slice from start [:stop]
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[:3].to_list()
        expected_sample_ids = [samples[i].sample_id for i in [0, 1, 2]]
        actual_sample_ids = [sample.sample_id for sample in result_samples]
        assert actual_sample_ids == expected_sample_ids

        # Test slice to end [start:]
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[2:].to_list()
        expected_sample_ids = [samples[i].sample_id for i in [2, 3, 4]]
        actual_sample_ids = [sample.sample_id for sample in result_samples]
        assert actual_sample_ids == expected_sample_ids

        # Test empty range (start beyond data)
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[10:15].to_list()
        assert len(result_samples) == 0

        # Test end greater than number of samples
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[3:10].to_list()
        expected_sample_ids = [samples[i].sample_id for i in [3, 4]]
        actual_sample_ids = [sample.sample_id for sample in result_samples]
        assert actual_sample_ids == expected_sample_ids

        # Test end <= start (empty result)
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[3:2].to_list()
        assert len(result_samples) == 0

        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name))[3:3].to_list()
        assert len(result_samples) == 0

    def test__getitem____returns_self_for_chaining(self, test_db: Session) -> None:
        """Test that __getitem__ returns self for method chaining."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act
        result = query[2:5]

        # Assert
        assert result is query
        assert query._slice == slice(2, 5)

    def test__getitem____integer_indexing_raises_error(self, test_db: Session) -> None:
        """Test that integer indexing raises TypeError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act & Assert
        with pytest.raises(
            TypeError,
            match="DatasetQuery only supports slice notation, not integer indexing",
        ):
            query[0]  # type: ignore[index]

    def test__getitem____slice_with_step_raises_error(self, test_db: Session) -> None:
        """Test that slice with step raises ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act & Assert
        with pytest.raises(ValueError, match="Strides are not supported"):
            query[::2]

    def test__getitem____negative_indices_raises_error(self, test_db: Session) -> None:
        """Test that negative indices raise ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Act & Assert
        with pytest.raises(ValueError, match="Negative indices are not supported"):
            query[-5:]

        with pytest.raises(ValueError, match="Negative indices are not supported"):
            query[:-5]

    def test__getitem____after_slice_raises_error(self, test_db: Session) -> None:
        """Test that using bracket notation after slice() raises ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.slice(limit=5)

        # Act & Assert
        with pytest.raises(
            ValueError, match="Cannot use bracket notation after slice\\(\\) has been called"
        ):
            query[2:5]

    def test_slice__after_getitem_raises_error(self, test_db: Session) -> None:
        """Test that calling slice() after bracket notation raises ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)
        query[2:5]

        # Act & Assert
        with pytest.raises(
            ValueError, match="slice\\(\\) can only be called once per DatasetQuery instance"
        ):
            query.slice(limit=3)
