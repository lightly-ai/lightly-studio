from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.sample_field import SampleField
from tests.helpers_resolvers import create_dataset, create_sample


class TestDatasetQueryOrderBy:
    def test_order_by__ascending_by_file_name(self, test_db: Session) -> None:
        """Test ordering samples by file name in ascending order."""
        # Arrange
        dataset = create_dataset(session=test_db)
        sample1 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/zebra.jpg",
            width=100,
            height=100,
        )
        sample2 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/alpha.jpg",
            width=200,
            height=200,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(OrderByField(SampleField.file_name)).to_list()

        # Assert
        assert len(result_samples) == 2
        # Should be ordered alphabetically: alpha.jpg, zebra.jpg
        assert result_samples[0].sample_id == sample2.sample_id  # alpha.jpg
        assert result_samples[1].sample_id == sample1.sample_id  # zebra.jpg

    def test_order_by__triple_criteria_width_height_file_name(self, test_db: Session) -> None:
        """Test ordering by triple criteria: width asc, height desc, file_name asc."""
        # Arrange
        dataset = create_dataset(session=test_db)
        sample1 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/E.jpg",
            width=100,  # Same width as sample2 and sample4
            height=150,
        )
        sample2 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/A.jpg",
            width=100,  # Same width as sample1 and sample4
            height=200,
        )
        sample3 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/B.jpg",
            width=200,  # Same width as sample5
            height=300,  # Same height as sample5 to test file_name ordering
        )
        sample4 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/C.jpg",
            width=100,  # Same width as sample1 and sample2
            height=100,  # Smallest height
        )
        sample5 = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/D.jpg",
            width=200,  # Same width as sample3
            height=300,  # Same height as sample3 to test file_name ordering
        )

        # Act: Triple criteria ordering (width asc, height desc, file_name asc)
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.order_by(
            OrderByField(SampleField.width),
            OrderByField(SampleField.height).desc(),
            OrderByField(SampleField.file_name).desc().asc(),
        ).to_list()

        # Assert
        assert len(result_samples) == 5
        # Expected order: width=100 by height desc (A=200, E=150, C=100),
        # width=200 by height desc, then by file_name asc (B=300, D=300)
        assert result_samples[0].sample_id == sample2.sample_id  # A.jpg, width=100, height=200
        assert result_samples[1].sample_id == sample1.sample_id  # E.jpg, width=100, height=150
        assert result_samples[2].sample_id == sample4.sample_id  # C.jpg, width=100, height=100
        assert result_samples[3].sample_id == sample3.sample_id  # B.jpg, width=200, height=300
        assert result_samples[4].sample_id == sample5.sample_id  # D.jpg, width=200, height=300

    def test_order_by__multiple_calls_raises_error(self, test_db: Session) -> None:
        """Test that calling order_by() twice raises ValueError."""
        # Arrange
        dataset = create_dataset(session=test_db)
        query = DatasetQuery(dataset=dataset, session=test_db)
        query.order_by(OrderByField(SampleField.file_name))

        # Act & Assert
        with pytest.raises(
            ValueError, match="order_by\\(\\) can only be called once per DatasetQuery instance"
        ):
            query.order_by(OrderByField(SampleField.file_name).desc())
