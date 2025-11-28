from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_dataset,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames, create_videos


def test_get_table_fields_bounds__without_annotations_frames(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4", fps=2, duration_s=5, width=200, height=250),
            VideoStub(path="/path/to/sample2.mp4", fps=3, duration_s=6, width=300, height=350),
            VideoStub(path="/path/to/sample3.mp4", fps=4, duration_s=7, width=400, height=450),
            VideoStub(path="/path/to/sample4.mp4", fps=5, duration_s=8, width=500, height=550),
        ],
    )

    bounds = video_resolver.get_table_fields_bounds(session=test_db, dataset_id=dataset_id)

    assert bounds is not None
    assert bounds.fps.min == 2
    assert bounds.fps.max == 5
    assert bounds.duration_s.min == 5
    assert bounds.duration_s.max == 8
    assert bounds.width.min == 200
    assert bounds.width.max == 500
    assert bounds.height.min == 250
    assert bounds.height.max == 550


def test_get_table_fields_bounds__with_annotations_frames(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    video_frame_id_1 = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample1.mp4", fps=5, duration_s=5, width=200, height=250),
    ).frame_sample_ids[0]
    video_frame_id_2 = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample2.mp4", fps=2, duration_s=8, width=300, height=450),
    ).frame_sample_ids[0]
    video_frame_id_3 = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/sample3.mp4", fps=30, duration_s=10, width=500, height=550),
    ).frame_sample_ids[0]

    car_label = create_annotation_label(
        session=test_db,
        annotation_label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        annotation_label_name="airplane",
    )

    # Create annotations
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_1,
        annotation_label_id=car_label.annotation_label_id,
        dataset_id=dataset_id,
    )

    create_annotation(
        session=test_db,
        sample_id=video_frame_id_2,
        annotation_label_id=car_label.annotation_label_id,
        dataset_id=dataset_id,
    )

    create_annotation(
        session=test_db,
        sample_id=video_frame_id_3,
        annotation_label_id=airplane_label.annotation_label_id,
        dataset_id=dataset_id,
    )

    bounds = video_resolver.get_table_fields_bounds(
        session=test_db,
        dataset_id=dataset_id,
        annotations_frames_labels_id=[car_label.annotation_label_id],
    )

    assert bounds is not None
    assert bounds.fps.min == 2
    assert bounds.fps.max == 5
    assert bounds.duration_s.min == 5
    assert bounds.duration_s.max == 8
    assert bounds.width.min == 200
    assert bounds.width.max == 300
    assert bounds.height.min == 250
    assert bounds.height.max == 450
