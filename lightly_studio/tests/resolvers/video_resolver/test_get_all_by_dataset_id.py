from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
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
        ],
    )

    # Act
    result = video_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert result.samples[0].file_name == "sample1.mp4"
    assert result.samples[1].file_name == "sample2.mp4"


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
        videos=[SampleVideo(file_path_abs=f"/sample{i}.mp4") for i in range(5)],
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
        ],
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
