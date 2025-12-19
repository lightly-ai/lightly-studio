from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    dataset_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_dataset,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


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
                duration_s=2.0,
                fps=1.0,
            )
        ],
    )[0]
    video_frames_dataset_id = dataset_resolver.get_or_create_child_dataset(
        session=test_db, dataset_id=dataset_id, sample_type=SampleType.VIDEO_FRAME
    )
    video_frame_resolver.create_many(
        session=test_db,
        dataset_id=video_frames_dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=1,
                frame_timestamp_s=1.0,
                frame_timestamp_pts=1,
                parent_sample_id=sample_video_2_id,
            ),
            VideoFrameCreate(
                frame_number=0,
                frame_timestamp_s=0.0,
                frame_timestamp_pts=0,
                parent_sample_id=sample_video_2_id,
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
                duration_s=2.0,
                fps=1.0,
            )
        ],
    )[0]
    video_frame_resolver.create_many(
        session=test_db,
        dataset_id=video_frames_dataset_id,
        samples=[
            VideoFrameCreate(
                frame_number=1,
                frame_timestamp_s=1.0,
                frame_timestamp_pts=1,
                parent_sample_id=sample_video_1_id,
            ),
            VideoFrameCreate(
                frame_number=0,
                frame_timestamp_s=0.0,
                frame_timestamp_pts=0,
                parent_sample_id=sample_video_1_id,
            ),
        ],
    )
    # Order after insertion (path, frame_number): (video2,1), (video2,0), (video1,1), (video1,0)

    # Act
    result = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=video_frames_dataset_id
    )

    # Assert
    assert len(result.samples) == 4
    assert result.total_count == 4
    assert result.samples[0].frame_number == 0
    assert result.samples[0].parent_sample_id == sample_video_1_id
    assert result.samples[1].frame_number == 1
    assert result.samples[1].parent_sample_id == sample_video_1_id
    assert result.samples[2].frame_number == 0
    assert result.samples[2].parent_sample_id == sample_video_2_id
    assert result.samples[3].frame_number == 1
    assert result.samples[3].parent_sample_id == sample_video_2_id


def test_get_all_by_dataset_id__with_frame_number_filter(test_db: Session) -> None:
    dataset_id = create_dataset(session=test_db, sample_type=SampleType.VIDEO).dataset_id

    video_frame_data = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample1.mp4", duration_s=5, fps=1),
    )

    samples = video_frame_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=video_frame_data.video_frames_dataset_id,
        video_frame_filter=VideoFrameFilter(
            frame_number=FilterDimensions(min=2, max=3),
        ),
    ).samples

    assert len(samples) == 2
    assert samples[0].sample_id == video_frame_data.frame_sample_ids[2]
    assert samples[1].sample_id == video_frame_data.frame_sample_ids[3]


def test_get_all_by_dataset_id__with_annotations_filter(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)

    # Create videos
    video_frame_data = create_video_with_frames(
        session=test_db,
        dataset_id=dataset.dataset_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    car_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset.dataset_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset.dataset_id,
        label_name="airplane",
    )

    # Create annotations
    create_annotation(
        session=test_db,
        sample_id=video_frame_data.frame_sample_ids[0],
        annotation_label_id=car_label.annotation_label_id,
        dataset_id=dataset.dataset_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        dataset_id=dataset.dataset_id,
    )

    samples = video_frame_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=video_frame_data.video_frames_dataset_id,
        video_frame_filter=VideoFrameFilter(
            sample_filter=SampleFilter(annotation_label_ids=[car_label.annotation_label_id])
        ),
    ).samples

    assert len(samples) == 1
    assert samples[0].sample_id == video_frame_data.frame_sample_ids[0]


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
        video=VideoStub(path="video1.mp4", duration_s=2.0, fps=1),  # 2 frames
    ).video_sample_id

    sample_video_2_id = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="video2.mp4", duration_s=3.0, fps=1),  # 3 frames
    ).video_sample_id

    video_frames_dataset_id = dataset_resolver.get_or_create_child_dataset(
        session=test_db, dataset_id=dataset_id, sample_type=SampleType.VIDEO_FRAME
    )
    # Act - Get first 2 samples
    result_page_1 = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=video_frames_dataset_id, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=video_frames_dataset_id, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=video_frames_dataset_id, pagination=Paginated(offset=4, limit=2)
    )

    # Assert - Check first page
    assert len(result_page_1.samples) == 2
    assert result_page_1.total_count == 5
    assert result_page_1.samples[0].frame_number == 0
    assert result_page_1.samples[0].parent_sample_id == sample_video_1_id
    assert result_page_1.samples[1].frame_number == 1
    assert result_page_1.samples[1].parent_sample_id == sample_video_1_id

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].frame_number == 0
    assert result_page_2.samples[0].parent_sample_id == sample_video_2_id
    assert result_page_2.samples[1].frame_number == 1
    assert result_page_2.samples[1].parent_sample_id == sample_video_2_id

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].frame_number == 2
    assert result_page_3.samples[0].parent_sample_id == sample_video_2_id

    # Assert - Check out of bounds (should return empty list)
    result_empty = video_frame_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=video_frames_dataset_id, pagination=Paginated(offset=5, limit=2)
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
    video_frames_dataset_id = dataset_resolver.get_or_create_child_dataset(
        session=test_db, dataset_id=dataset_id, sample_type=SampleType.VIDEO_FRAME
    )
    result = video_frame_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=video_frames_dataset_id,
        video_frame_filter=VideoFrameFilter(sample_filter=SampleFilter(sample_ids=sample_ids)),
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)


def test_get_all_by_dataset_id__with_video_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)

    video_frames = create_video_with_frames(
        session=test_db,
        dataset_id=dataset.dataset_id,
        video=VideoStub(path="video1.mp4", duration_s=1, fps=2),
    )

    create_video_with_frames(
        session=test_db,
        dataset_id=dataset.dataset_id,
        video=VideoStub(path="video2.mp4", duration_s=1, fps=2),
    )

    result = video_frame_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=video_frames.video_frames_dataset_id,
        video_frame_filter=VideoFrameFilter(video_id=video_frames.video_sample_id),
    )

    assert len(result.samples) == 2
    assert result.total_count == 2

    assert result.samples[0].frame_number == 0
    assert result.samples[0].parent_sample_id == video_frames.video_sample_id

    assert result.samples[1].frame_number == 1
    assert result.samples[1].parent_sample_id == video_frames.video_sample_id
