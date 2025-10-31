from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.resolvers import (
    tag_resolver,
    video_resolver,
)
from lightly_studio.resolvers.samples_filter import (
    FilterDimensions,
    SampleFilter,
)
from tests.helpers_resolvers import (
    create_dataset,
    create_tag,
)
from tests.resolvers.video_resolver.helper import SampleVideo, create_videos


def test_get_all_by_dataset_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # create samples out of order to verify ordering by file_path_abs
    _ = create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            SampleVideo(file_path_abs="/path/to/sample2.mp4"),
            SampleVideo(file_path_abs="/path/to/sample1.mp4"),
        ]
    )

    # Act
    result = video_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert result.samples[0].file_name == "sample1.mp4"
    assert result.samples[1].file_name == "sample2.mmp4"


def test_get_all_by_dataset_id__with_pagination(
    test_db: Session,
) -> None:
    # Arrange
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create sample data with known sample_ids to ensure consistent ordering
    videos = create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            SampleVideo(file_path_abs=f"/sample{i}.mp4")
            for i in range(5)
        ]
    )

    # Sort samples by sample_id to match the expected order
    videos.sort(key=lambda x: x.file_name)

    # Act - Get first 2 samples
    result_page_1 = video_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = video_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = video_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=4, limit=2)
    )

    # Assert - Check first page
    assert len(result_page_1.samples) == 2
    assert result_page_1.total_count == 5
    assert result_page_1.samples[0].file_name == videos[0].file_name
    assert result_page_1.samples[1].file_name == videos[1].file_name

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].file_name == videos[2].file_name
    assert result_page_2.samples[1].file_name == videos[3].file_name

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].file_name == videos[4].file_name

    # Assert - Check out of bounds (should return empty list)
    result_empty = video_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=5, limit=2)
    )
    assert len(result_empty.samples) == 0
    assert result_empty.total_count == 5


def test_get_all_by_dataset_id__empty_output(
    test_db: Session,
) -> None:
    # Arrange
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Act
    result = video_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 0  # Should return an empty list
    assert result.total_count == 0


def test_get_all_by_dataset_id__with_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples

    videos = create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            SampleVideo(file_path_abs="/path/to/sample1.mp4"),
            SampleVideo(file_path_abs="/path/to/sample2.mp4"),
            SampleVideo(file_path_abs="/path/to/sample3.mp4"),
        ]
    )

    sample_ids = [videos[1].sample_id, videos[2].sample_id]

    result = video_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)

def test_get_all_by_dataset_id__with_dimension_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    _ = create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            SampleVideo(file_path_abs="/path/to/small.mp4", width=100, height=200),
            SampleVideo(file_path_abs="/path/to/medium.mp4", width=800, height=600),
            SampleVideo(file_path_abs="/path/to/large.mp4", width=1929, height=1080),
        ]
    )

    # Test width filtering
    result = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
            width=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.width >= 500 for s in result.samples)

    # Test height filtering
    result = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
            height=FilterDimensions(max=700),
        ),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.height <= 700 for s in result.samples)

    # Test combined filtering
    result = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
            width=FilterDimensions(min=500, max=1000),
            height=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 1
    assert result.total_count == 1
    assert result.samples[0].file_name == "medium.mp4"

def test_get_all_by_dataset_id__with_tag_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_part1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_1",
        kind="sample",
    )
    tag_part2 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_2",
        kind="sample",
    )

    total_samples = 10
    videos = create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            SampleVideo(file_path_abs=f"/sample{i}.mp4")
            for i in range(total_samples)
        ]
    )

    # add first half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_part1.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(videos) if i < total_samples / 2],
    )

    # add second half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_part2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(videos) if i >= total_samples / 2],
    )

    # Test filtering by tags
    result_part1 = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(tag_ids=[tag_part1.tag_id]),
    )
    assert len(result_part1.samples) == int(total_samples / 2)
    assert result_part1.total_count == int(total_samples / 2)
    assert result_part1.samples[0].file_path_abs == "sample0.mp4"

    result_part2 = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(tag_ids=[tag_part2.tag_id]),
    )
    assert len(result_part2.samples) == int(total_samples / 2)
    assert result_part2.total_count == int(total_samples / 2)
    assert result_part2.samples[0].file_path_abs == "sample5.mp4"

    # test filtering by both tags
    result_all = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
            tag_ids=[
                tag_part1.tag_id,
                tag_part2.tag_id,
            ],
        ),
    )
    assert len(result_all.samples) == int(total_samples)
    assert result_all.total_count == int(total_samples)
