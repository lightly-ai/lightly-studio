"""Tests for SampleFilter class."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.samples_filter import (
    FilterDimensions,
    SampleFilter,
)
from tests.helpers_resolvers import (
    SampleImage,
    create_annotation,
    create_annotation_label,
    create_dataset,
    create_image,
    create_images,
    create_tag,
)


class TestSampleFilter:
    @pytest.fixture
    def setup_samples_filter_test(self, test_db: Session) -> tuple[list[ImageTable], UUID, Session]:
        """Create sample data for testing."""
        dataset = create_dataset(session=test_db)
        dataset_id = dataset.dataset_id

        samples = [
            create_image(
                session=test_db,
                dataset_id=dataset_id,
                file_path_abs=f"/path/to/sample_{i}.jpg",
                width=width,
                height=height,
            )
            for i, (width, height) in enumerate(
                [
                    (100, 200),  # narrow, tall
                    (800, 600),  # medium, standard
                    (1920, 1080),  # wide, HD
                    (3840, 2160),  # very wide, 4K
                    (400, 400),  # square
                ]
            )
        ]

        # just pass the session to the resolver
        return samples, dataset_id, test_db

    @pytest.mark.parametrize(
        (
            "width_filter",
            "height_filter",
            "expected_count",
            "expected_condition",
        ),
        [
            # No filters
            (None, None, 5, lambda _: True),
            # Width filters
            (FilterDimensions(min=500), None, 3, lambda s: s.width >= 500),
            (FilterDimensions(max=1000), None, 3, lambda s: s.width <= 1000),
            (
                FilterDimensions(min=400, max=2000),
                None,
                3,
                lambda s: 400 <= s.width <= 2000,
            ),
            # Height filters
            (None, FilterDimensions(min=600), 3, lambda s: s.height >= 600),
            (None, FilterDimensions(max=500), 2, lambda s: s.height <= 500),
            (
                None,
                FilterDimensions(min=300, max=1000),
                2,
                lambda s: 300 <= s.height <= 1000,
            ),
            # Combined filters
            (
                FilterDimensions(min=500),
                FilterDimensions(max=1500),
                2,
                lambda s: s.width >= 500 and s.height <= 1500,
            ),
        ],
    )
    def test_samples_filter_dimensions(
        self,
        setup_samples_filter_test: tuple[list[ImageTable], UUID, Session],
        width_filter: FilterDimensions | None,
        height_filter: FilterDimensions | None,
        expected_count: int,
        expected_condition: Callable[[ImageTable], bool],
    ) -> None:
        """Test SampleFilter with dimension filters."""
        samples, dataset_id, session = setup_samples_filter_test

        # Create the base query.
        query = select(ImageTable)

        # Create the filter.
        sample_filter = SampleFilter(
            width=width_filter,
            height=height_filter,
        )

        # Apply the filter.
        filtered_query = sample_filter.apply(query=query)
        result = session.exec(filtered_query).all()

        assert len(result) == expected_count
        assert all(expected_condition(sample) for sample in result)

    def test_samples_filter_dimentions__apply_filters(
        self, setup_samples_filter_test: tuple[list[ImageTable], UUID, Session]
    ) -> None:
        """Test that apply_filters calls apply_dimensions_filters."""
        samples, dataset_id, session = setup_samples_filter_test

        # Create a filter with specific dimensions
        width_filter = FilterDimensions(min=500, max=2000)
        height_filter = FilterDimensions(min=500, max=1200)

        # Create the base query.
        query = select(ImageTable)

        # Create the filter.
        sample_filter = SampleFilter(
            width=width_filter,
            height=height_filter,
        )

        # Apply the filter.
        filtered_query = sample_filter.apply(query=query)
        result = session.exec(filtered_query).all()

        # Should match only samples that satisfy both width
        # and height conditions
        def expected_condition(s: ImageTable) -> bool:
            return 500 <= s.width <= 2000 and 500 <= s.height <= 1200

        expected_count = 2  # Based on our test data

        assert len(result) == expected_count
        assert all(expected_condition(sample) for sample in result)

    def test_samples_filter_annotation_filters(
        self,
        test_db: Session,
        setup_samples_filter_test: tuple[list[ImageTable], UUID, Session],
    ) -> None:
        """Test SampleFilter with annotation label filters."""
        samples, dataset_id, session = setup_samples_filter_test

        # Create annotation labels
        cat_label = create_annotation_label(session=test_db, annotation_label_name="cat")
        dog_label = create_annotation_label(session=test_db, annotation_label_name="dog")

        # Add annotations to samples
        create_annotation(
            session=test_db,
            dataset_id=dataset_id,
            sample_id=samples[0].sample_id,
            annotation_label_id=cat_label.annotation_label_id,
        )
        create_annotation(
            session=test_db,
            dataset_id=dataset_id,
            sample_id=samples[1].sample_id,
            annotation_label_id=dog_label.annotation_label_id,
        )

        # Create the base query.
        query = select(ImageTable)

        # Create the filter.
        sample_filter = SampleFilter(
            annotation_label_ids=[cat_label.annotation_label_id],
        )

        # Apply the filter
        filtered_query = sample_filter.apply(query=query)
        result = session.exec(filtered_query).all()

        # Should only return samples with cat annotations
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_samples_filter_tag_filters(
        self,
        test_db: Session,
        setup_samples_filter_test: tuple[list[ImageTable], UUID, Session],
    ) -> None:
        """Test SampleFilter with tag filters."""
        samples, dataset_id, session = setup_samples_filter_test

        # Create tags
        tag1 = create_tag(
            session=test_db,
            dataset_id=dataset_id,
            tag_name="tag1",
            kind="sample",
        )
        tag2 = create_tag(
            session=test_db,
            dataset_id=dataset_id,
            tag_name="tag2",
            kind="sample",
        )

        # Add samples to tags
        tag_resolver.add_sample_ids_to_tag_id(
            session=test_db,
            tag_id=tag1.tag_id,
            sample_ids=[samples[0].sample_id],
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=test_db,
            tag_id=tag2.tag_id,
            sample_ids=[samples[1].sample_id],
        )

        # Create the base query.
        query = select(ImageTable)

        # Create the filter with tag1
        sample_filter = SampleFilter(
            tag_ids=[tag1.tag_id],
        )

        # Create and apply the filter
        filtered_query = sample_filter.apply(query=query)
        result = session.exec(filtered_query).all()

        # Should only return samples with tag1
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_samples_filter_annotation_filters__distinct_samples_only(
        self,
        test_db: Session,
        setup_samples_filter_test: tuple[list[ImageTable], UUID, Session],
    ) -> None:
        """Test SampleFilter with annotation label filters.

        Samples with multiple annotations of the same label should appear only
        once.
        """
        samples, dataset_id, session = setup_samples_filter_test

        # Create annotation labels
        cat_label = create_annotation_label(session=test_db, annotation_label_name="cat")
        dog_label = create_annotation_label(session=test_db, annotation_label_name="dog")

        # Add 3 cat annotations to the first sample.
        for _ in range(3):
            create_annotation(
                session=test_db,
                dataset_id=dataset_id,
                sample_id=samples[0].sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            )

        # Add a dog annotation to the second sample.
        create_annotation(
            session=test_db,
            dataset_id=dataset_id,
            sample_id=samples[1].sample_id,
            annotation_label_id=dog_label.annotation_label_id,
        )

        # Create the base query.
        query = select(ImageTable)

        # Create the filter to only get samples with at least one cat.
        sample_filter = SampleFilter(
            annotation_label_ids=[cat_label.annotation_label_id],
        )

        # Apply the filter
        filtered_query = sample_filter.apply(query=query)
        result = session.exec(filtered_query).all()

        # Should only return the sample with the cat annotations ONCE.
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_samples_filter_tag_filters__distinct_samples_only(
        self,
        test_db: Session,
        setup_samples_filter_test: tuple[list[ImageTable], UUID, Session],
    ) -> None:
        """Test SampleFilter with tag filters."""
        samples, dataset_id, session = setup_samples_filter_test

        # Create tags
        tag1 = create_tag(
            session=test_db,
            dataset_id=dataset_id,
            tag_name="tag1",
            kind="sample",
        )
        tag2 = create_tag(
            session=test_db,
            dataset_id=dataset_id,
            tag_name="tag2",
            kind="sample",
        )

        # Add the first tag to the first 3 samples.
        for i in range(3):
            tag_resolver.add_sample_ids_to_tag_id(
                session=test_db,
                tag_id=tag1.tag_id,
                sample_ids=[samples[i].sample_id],
            )

        # Add the second tag to the last 3 samples
        # (third one would have both tags).
        for i in range(2, 5):
            tag_resolver.add_sample_ids_to_tag_id(
                session=test_db,
                tag_id=tag2.tag_id,
                sample_ids=[samples[i].sample_id],
            )

        # Create the base query.
        query = select(ImageTable)

        # Create the filter with tag1
        sample_filter = SampleFilter(
            tag_ids=[tag1.tag_id, tag2.tag_id],
        )

        # Create and apply the filter
        filtered_query = sample_filter.apply(query=query)
        result = session.exec(filtered_query).all()

        # Should return all samples only once.
        assert len(result) == 5
        # A single sample should have 2 tags.
        assert sum(1 for r in result if len(r.sample.tags) == 2) == 1

    def test_samples_filter__sample_ids_with_dimension_filter(
        self,
        test_db: Session,
    ) -> None:
        """Sample IDs should be applied alongside other filters."""
        dataset = create_dataset(session=test_db)
        dataset_id = dataset.dataset_id

        samples = create_images(
            db_session=test_db,
            dataset_id=dataset_id,
            images=[
                SampleImage(path="sample_0.png", width=300),
                SampleImage(path="sample_1.png", width=300),
                SampleImage(path="sample_2.png", width=100),
                SampleImage(path="sample_3.png", width=400),
                SampleImage(path="sample_4.png", width=500),
            ],
        )

        query = select(ImageTable).order_by(
            col(ImageTable.created_at).asc(),
            col(ImageTable.sample_id).asc(),
        )
        sample_filter = SampleFilter(
            sample_ids=[
                samples[1].sample_id,
                samples[2].sample_id,
                samples[3].sample_id,
            ],
            width=FilterDimensions(min=200),
        )

        filtered_query = sample_filter.apply(query=query)
        result = test_db.exec(filtered_query).all()

        # Sample with index 2 does not fulfil the width filter.
        expected_samples = [samples[1], samples[3]]
        assert [sample.sample_id for sample in result] == [
            sample.sample_id for sample in expected_samples
        ]
