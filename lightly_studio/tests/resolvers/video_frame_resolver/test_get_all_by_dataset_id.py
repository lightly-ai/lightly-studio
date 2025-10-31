from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.resolvers import (
    video_frame_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_frame_resolver.helpers import SampleVideo, create_video_with_frames


def test_get_all_by_dataset_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # create samples out of order to verify ordering by file_path_abs
    sample_video_2, _ = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=SampleVideo(file_path_abs="video2.mp4"),  # first video2
        invert_frame_sorting=True,  # creates frame in order 1, 0
    )

    sample_video_1, _ = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=SampleVideo(file_path_abs="video1.mp4"),  # second video1
    )
    # Order after insertion (path, frame_number): (video2,1), (video2,0), (video1,0), (video1,1)

    # Act
    result = video_frame_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 4
    assert result.total_count == 4
    assert result.samples[0].frame_number == 0
    assert result.samples[0].video_sample_id == sample_video_1.sample_id
    assert result.samples[1].frame_number == 1
    assert result.samples[1].video_sample_id == sample_video_1.sample_id
    assert result.samples[2].frame_number == 0
    assert result.samples[2].video_sample_id == sample_video_2.sample_id
    assert result.samples[3].frame_number == 1
    assert result.samples[3].video_sample_id == sample_video_2.sample_id


def test_get_all_by_dataset_id__with_pagination(
    test_db: Session,
) -> None:
    # Arrange
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create sample data with known sample_ids to ensure consistent ordering
    sample_video_1, _ = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=SampleVideo(file_path_abs="video1.mp4"),  # 2 frames
    )

    sample_video_2, _ = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=SampleVideo(file_path_abs="video2.mp4", duration=1.5),  # 3 frames
    )

    # Act - Get first 2 samples
    result_page_1 = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=4, limit=2)
    )

    # Assert - Check first page
    assert len(result_page_1.samples) == 2
    assert result_page_1.total_count == 5
    assert result_page_1.samples[0].frame_number == 0
    assert result_page_1.samples[0].video_sample_id == sample_video_1.sample_id
    assert result_page_1.samples[1].frame_number == 1
    assert result_page_1.samples[1].video_sample_id == sample_video_1.sample_id

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].frame_number == 0
    assert result_page_2.samples[0].video_sample_id == sample_video_2.sample_id
    assert result_page_2.samples[1].frame_number == 1
    assert result_page_2.samples[1].video_sample_id == sample_video_2.sample_id

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].frame_number == 2
    assert result_page_3.samples[0].video_sample_id == sample_video_2.sample_id

    # Assert - Check out of bounds (should return empty list)
    result_empty = video_frame_resolver.get_all_by_dataset_id(
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
    result = video_frame_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 0  # Should return an empty list
    assert result.total_count == 0


def test_get_all_by_dataset_id__with_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create sample data with known sample_ids
    _, sample_frames = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=SampleVideo(file_path_abs="video1.mp4", duration=2),  # 4 frames
    )

    sample_ids = [sample_frames[1].sample_id, sample_frames[2].sample_id]

    result = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)
