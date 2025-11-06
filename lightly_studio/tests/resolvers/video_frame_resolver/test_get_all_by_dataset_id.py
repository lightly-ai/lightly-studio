from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    video_frame_resolver,
    video_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_frame_resolver.helpers import create_video_with_frames
from tests.resolvers.video_resolver.helpers import VideoStub


def test_get_all_by_dataset_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    # create samples out of order to verify ordering by parent video file_path_abs and frame number
    sample_video_2_id = video_resolver.create_many(
        session=test_db,
        dataset_id=dataset_id,
        samples=[
            VideoCreate(
                file_path_abs="video2.mp4",
                file_name="video2.mp4",
                width=100,
                height=200,
                duration=2.0,
                fps=1.0,
            )
        ],
    )[0]
    video_frame_resolver.create_many(
        session=test_db,
        dataset_id=dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=1, frame_timestamp=1.0, video_sample_id=sample_video_2_id
            ),
            VideoFrameCreate(
                frame_number=0, frame_timestamp=0.0, video_sample_id=sample_video_2_id
            ),
        ],
    )
    sample_video_1_id = video_resolver.create_many(
        session=test_db,
        dataset_id=dataset_id,
        samples=[
            VideoCreate(
                file_path_abs="video1.mp4",
                file_name="video1.mp4",
                width=100,
                height=200,
                duration=2.0,
                fps=1.0,
            )
        ],
    )[0]
    video_frame_resolver.create_many(
        session=test_db,
        dataset_id=dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=1, frame_timestamp=1.0, video_sample_id=sample_video_1_id
            ),
            VideoFrameCreate(
                frame_number=0, frame_timestamp=0.0, video_sample_id=sample_video_1_id
            ),
        ],
    )
    # Order after insertion (path, frame_number): (video2,1), (video2,0), (video1,1), (video1,0)

    # Act
    result = video_frame_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 4
    assert result.total_count == 4
    assert result.samples[0].frame_number == 0
    assert result.samples[0].video_sample_id == sample_video_1_id
    assert result.samples[1].frame_number == 1
    assert result.samples[1].video_sample_id == sample_video_1_id
    assert result.samples[2].frame_number == 0
    assert result.samples[2].video_sample_id == sample_video_2_id
    assert result.samples[3].frame_number == 1
    assert result.samples[3].video_sample_id == sample_video_2_id


def test_get_all_by_dataset_id__with_pagination(
    test_db: Session,
) -> None:
    # Arrange
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    # Create sample data with known sample_ids to ensure consistent ordering
    sample_video_1_id = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="video1.mp4", duration=2.0, fps=1),  # 2 frames
    ).video_sample_id

    sample_video_2_id = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="video2.mp4", duration=3.0, fps=1),  # 3 frames
    ).video_sample_id

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
    assert result_page_1.samples[0].video_sample_id == sample_video_1_id
    assert result_page_1.samples[1].frame_number == 1
    assert result_page_1.samples[1].video_sample_id == sample_video_1_id

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].frame_number == 0
    assert result_page_2.samples[0].video_sample_id == sample_video_2_id
    assert result_page_2.samples[1].frame_number == 1
    assert result_page_2.samples[1].video_sample_id == sample_video_2_id

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].frame_number == 2
    assert result_page_3.samples[0].video_sample_id == sample_video_2_id

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
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    # Act
    result = video_frame_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 0
    assert result.total_count == 0


def test_get_all_by_dataset_id__with_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    # Create sample data with known sample_ids
    sample_ids = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(),
    ).frame_sample_ids

    result = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)
