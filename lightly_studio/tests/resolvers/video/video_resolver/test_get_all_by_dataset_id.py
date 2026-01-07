import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import SampleType
from lightly_studio.models.range import FloatRange
from lightly_studio.resolvers import (
    metadata_resolver,
    video_resolver,
)
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_sample_embedding,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames, create_videos


def test_get_all_by_collection_id(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # create samples out of order to verify ordering by file_path_abs
    create_videos(
        session=test_db,
        collection_id=collection_id,
        videos=[
            VideoStub(path="/path/to/sample2.mp4"),
            VideoStub(path="/path/to/sample1.mp4"),
        ],
    )

    # Act
    result = video_resolver.get_all_by_collection_id(session=test_db, collection_id=collection_id)

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert result.samples[0].file_name == "sample1.mp4"
    assert result.samples[1].file_name == "sample2.mp4"


def test_get_all_by_collection_id__first_frame(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="video1.mp4", duration_s=2.0, fps=1),  # 2 frames
    )

    # Act
    result = video_resolver.get_all_by_collection_id(session=test_db, collection_id=collection_id)

    # Assert
    assert len(result.samples) == 1
    assert result.samples[0].file_name == "video1.mp4"
    assert result.samples[0].frame
    assert result.samples[0].frame.frame_number == 0


def test_get_all_by_collection_id__with_pagination(
    test_db: Session,
) -> None:
    # Arrange
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create sample data with known sample_ids to ensure consistent ordering
    video_ids = create_videos(
        session=test_db,
        collection_id=collection_id,
        videos=[VideoStub(path=f"/sample{i}.mp4") for i in range(5)],
    )

    # Sort samples by sample_id to match the expected order
    videos = video_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id, sample_ids=video_ids
    ).samples

    # Act - Get first 2 samples
    result_page_1 = video_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = video_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = video_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id, pagination=Paginated(offset=4, limit=2)
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
    result_empty = video_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id, pagination=Paginated(offset=5, limit=2)
    )
    assert len(result_empty.samples) == 0
    assert result_empty.total_count == 5


def test_get_all_by_collection_id__empty_output(
    test_db: Session,
) -> None:
    # Arrange
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    # Act
    result = video_resolver.get_all_by_collection_id(session=test_db, collection_id=collection_id)

    # Assert
    assert len(result.samples) == 0  # Should return an empty list
    assert result.total_count == 0


def test_get_all_by_collection_id__with_sample_ids(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create samples
    video_ids = create_videos(
        session=test_db,
        collection_id=collection_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
            VideoStub(path="/path/to/sample3.mp4"),
        ],
    )

    sample_ids = [video_ids[1], video_ids[2]]

    result = video_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)


def test_get_all_by_collection_id_with_frames(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="video1.mp4", duration_s=2.0, fps=1),  # 2 frames
    )

    result = video_resolver.get_all_by_collection_id_with_frames(
        session=test_db, collection_id=collection_id
    )

    # Assert
    assert len(result) == 1
    assert result[0].file_name == "video1.mp4"
    assert result[0].frames is not None
    assert len(result[0].frames) == 2
    assert result[0].frames[0].frame_number == 0
    assert result[0].frames[1].frame_number == 1


def test_get_all_by_collection_id__with_annotation_frames_label_filter(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    video_frames_data_1 = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    video_frame_id = video_frames_data.frame_sample_ids[0]
    video_frame_id_1 = video_frames_data_1.frame_sample_ids[0]
    video_sample_id = video_frames_data.video_sample_id

    car_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="airplane",
    )

    # Create annotations
    car_annotation = create_annotation(
        session=test_db,
        sample_id=video_frame_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )

    result = video_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        filters=VideoFilter(annotation_frames_label_ids=[car_label.annotation_label_id]),
    )

    samples = result.samples
    sample = samples[0]
    assert len(samples) == 1

    assert sample.sample_id == video_sample_id
    assert sample.frame is not None
    assert sample.frame.sample.annotations[0].sample_id == car_annotation.sample_id


def test_get_all_by_collection_id__with_width_and_height_filter(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4", width=800, height=800),
    )

    video_sample_id = video_frames_data.video_sample_id

    max_width, max_height = (700, 700)

    result = video_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        filters=VideoFilter(
            width=FilterDimensions(
                min=0,
                max=max_width,
            ),
            height=FilterDimensions(
                min=0,
                max=max_height,
            ),
        ),
    )

    samples = result.samples
    assert len(samples) == 1
    assert samples[0].sample_id == video_sample_id
    assert samples[0].width <= max_width
    assert samples[0].height <= max_height


def test_get_all_by_collection_id__with_metadata_filter(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4", width=800, height=800),
    )

    video_sample_id = video_frames_data.video_sample_id

    metadata_resolver.set_value_for_sample(
        session=test_db,
        sample_id=video_sample_id,
        key="rotation",
        value=90,
    )

    samples = video_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        filters=VideoFilter(
            sample_filter=SampleFilter(
                metadata_filters=[MetadataFilter(key="rotation", op="==", value=90)]
            ),
        ),
    ).samples

    sample = samples[0]
    assert len(samples) == 1
    assert sample.sample_id == video_sample_id
    assert sample.sample.metadata_dict is not None
    assert sample.sample.metadata_dict.data["rotation"] == 90


def test_get_all_by_collection_id__with_fps_filter(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4", fps=5),
    )

    create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4", fps=2),
    )

    video_sample_id = video_frames_data.video_sample_id

    min_fps, max_fps = (3, 8)

    samples = video_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        filters=VideoFilter(
            fps=FloatRange(
                min=min_fps,
                max=max_fps,
            ),
        ),
    ).samples

    assert len(samples) == 1
    assert samples[0].sample_id == video_sample_id
    assert samples[0].fps >= min_fps
    assert samples[0].fps <= max_fps


def test_get_all_by_collection_id__with_duration_filter(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4", duration_s=10),
    )

    create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4", duration_s=5),
    )

    video_sample_id = video_frames_data.video_sample_id

    min_duration_s, max_duration_s = (6, 10)

    samples = video_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        filters=VideoFilter(
            duration_s=FloatRange(
                min=min_duration_s,
                max=max_duration_s,
            ),
        ),
    ).samples

    sample = samples[0]
    assert len(samples) == 1
    assert sample.sample_id == video_sample_id
    assert sample.duration_s is not None
    assert sample.duration_s >= min_duration_s
    assert sample.duration_s <= max_duration_s


def test_get_all_by_collection_id__with_embedding_sort(test_db: Session) -> None:
    """Test that videos are sorted by similarity and scores are returned."""
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="test_embedding_model",
        embedding_dimension=3,
    )

    # Create videos with frames.
    video1_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/video1.mp4"),
    )
    video2_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/video2.mp4"),
    )
    video3_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/video3.mp4"),
    )

    # Create embeddings for videos.
    create_sample_embedding(
        session=test_db,
        sample_id=video1_data.video_sample_id,
        embedding=[1.0, 1.0, 1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=test_db,
        sample_id=video2_data.video_sample_id,
        embedding=[-1.0, -1.0, -1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=test_db,
        sample_id=video3_data.video_sample_id,
        embedding=[1.0, 1.0, 2.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    # Retrieve videos ordered by similarity to embedding [-1, -1, -1].
    result = video_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        text_embedding=[-1.0, -1.0, -1.0],
    )

    # Assert videos are sorted by similarity (video2 is most similar).
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == video2_data.video_sample_id
    assert result.samples[1].sample_id == video3_data.video_sample_id
    assert result.samples[2].sample_id == video1_data.video_sample_id

    # Verify similarity scores are returned and in descending order.
    assert result.samples[0].similarity_score is not None
    assert result.samples[1].similarity_score is not None
    assert result.samples[2].similarity_score is not None
    assert result.samples[0].similarity_score == pytest.approx(1.0, abs=0.01)
    assert result.samples[0].similarity_score >= result.samples[1].similarity_score
    assert result.samples[1].similarity_score >= result.samples[2].similarity_score
