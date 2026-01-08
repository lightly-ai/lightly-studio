from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField
from tests.helpers_resolvers import create_collection, create_image


class TestDatasetQuery:
    def test_to_list__default_ordering_by_created_at(self, test_db: Session) -> None:
        """Test that samples are ordered by created_at when no explicit ordering is specified."""
        # Arrange
        dataset = create_collection(session=test_db)

        # Create newer sample first (to ensure db insertion order != created_at order)
        newer_image = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/newer.jpg",
            width=200,
            height=200,
        )
        # Update created_at to be newer
        newer_image.created_at = datetime(2024, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        test_db.add(newer_image)
        test_db.commit()
        test_db.refresh(newer_image)

        # Create older sample second
        older_image = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/older.jpg",
            width=100,
            height=100,
        )
        # Update created_at to be older
        older_image.created_at = datetime(2023, 12, 31, 10, 0, 0, tzinfo=timezone.utc)
        test_db.add(older_image)
        test_db.commit()
        test_db.refresh(older_image)

        # Act - execute query without any explicit ordering
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = query.to_list()

        # Assert - samples should be ordered by created_at in ascending order
        assert len(result_samples) == 2
        assert result_samples[0].created_at < result_samples[1].created_at
        assert result_samples[0].sample_id == older_image.sample_id
        assert result_samples[1].sample_id == newer_image.sample_id

    def test_to_list__all_operations_combined(self, test_db: Session) -> None:
        """Test all operations combined."""
        # Arrange
        dataset = create_collection(session=test_db)
        create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/zebra.jpg",
            width=100,
            height=100,
        )
        create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/alpha.jpg",
            width=150,
            height=150,
        )
        create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/beta.jpg",
            width=300,  # This will be filtered out
            height=300,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)
        result_samples = (
            query.match(ImageSampleField.width < 200)
            .order_by(OrderByField(ImageSampleField.file_name).desc())
            .slice(offset=0, limit=3)
            .to_list()
        )

        # Assert
        assert len(result_samples) == 2
        # Should be ordered reverse alphabetically: zebra.jpg, alpha.jpg
        assert result_samples[0].file_name == "zebra.jpg"
        assert result_samples[1].file_name == "alpha.jpg"

    def test_iter(self, test_db: Session) -> None:
        """Test that iterating over DatasetQuery yields samples correctly."""
        # Arrange
        dataset = create_collection(session=test_db)
        image1 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample1.png",
        )
        image2 = create_image(
            session=test_db,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/sample2.png",
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=test_db)

        # Assert
        it = iter(query)
        assert next(it).sample_id == image1.sample_id
        assert next(it).sample_id == image2.sample_id
        with pytest.raises(StopIteration):
            next(it)
