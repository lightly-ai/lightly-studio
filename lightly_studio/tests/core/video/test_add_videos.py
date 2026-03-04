from __future__ import annotations

import os
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import fsspec
import pytest
from av import container
from av.codec.context import ThreadType
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox, BoundingBoxFormat
from labelformat.model.category import Category
from labelformat.model.instance_segmentation_track import (
    SingleInstanceSegmentationTrack,
    VideoInstanceSegmentationTrack,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.object_detection_track import (
    ObjectDetectionTrackInput,
    SingleObjectDetectionTrack,
    VideoObjectDetectionTrack,
)
from labelformat.model.video import Video
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.video import add_videos, video_dataset
from lightly_studio.core.video.add_videos import FrameExtractionContext
from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    video_frame_resolver,
    video_resolver,
)
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import create_video_file


def test_load_into_collection_from_paths(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    # Create two temporary video files.
    first_video_path = create_video_file(
        output_path=tmp_path / "test_video_1.mp4",
        width=640,
        height=480,
        num_frames=30,
        fps=2,
    )
    second_video_path = create_video_file(
        output_path=tmp_path / "test_video_0.mp4",
        width=640,
        height=480,
        num_frames=30,
        fps=2,
    )
    video_sample_ids, frame_sample_ids = add_videos.load_into_dataset_from_paths(
        session=db_session,
        dataset_id=collection.collection_id,
        video_paths=[str(first_video_path), str(second_video_path)],
    )
    assert len(video_sample_ids) == 2
    assert len(frame_sample_ids) == 60

    # Check that video samples are created.
    videos = video_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    ).samples
    assert len(videos) == 2

    video = videos[0]
    assert video.file_name == "test_video_0.mp4"
    assert video.file_path_abs == str(second_video_path)
    assert video.frame is not None
    assert video.frame.frame_number == 0
    video = videos[1]
    assert video.file_name == "test_video_1.mp4"
    assert video.file_path_abs == str(first_video_path)

    # Check the correct collection hierarchy was created. There should be one extra collection
    # created with the video frames.
    collection_hierarchy = collection_resolver.get_hierarchy(
        session=db_session,
        dataset_id=collection.collection_id,
    )
    assert len(collection_hierarchy) == 2
    assert collection_hierarchy[0].sample_type == SampleType.VIDEO
    assert collection_hierarchy[1].sample_type == SampleType.VIDEO_FRAME

    video_frames = video_frame_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_hierarchy[1].collection_id,
    ).samples
    assert len(video_frames) == 60


def test__create_video_frame_samples(db_session: Session, tmp_path: Path) -> None:
    """Test _create_video_frame_samples function directly."""
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)

    # Create a temporary video file
    video_path = create_video_file(
        output_path=tmp_path / "test_video_frames.mp4",
        width=320,
        height=240,
        num_frames=2,
        fps=1,
    )

    # Create video sample in database
    video_sample_ids = video_resolver.create_many(
        session=db_session,
        collection_id=collection.collection_id,
        samples=[
            VideoCreate(
                file_path_abs=str(video_path),
                file_name=video_path.name,
                width=320,
                height=240,
                duration_s=2.0,  # 2 frames / 1 fps = 2 seconds
                fps=1,
            )
        ],
    )
    assert len(video_sample_ids) == 1
    video_sample_id = video_sample_ids[0]

    # Create video frames collection
    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )

    fs, fs_path = fsspec.core.url_to_fs(url=str(video_path))
    video_file = fs.open(path=fs_path, mode="rb")
    video_container = container.open(file=video_file)

    frame_sample_ids = add_videos._create_video_frame_samples(
        context=FrameExtractionContext(
            session=db_session,
            collection_id=video_frames_collection_id,
            video_sample_id=video_sample_id,
        ),
        video_container=video_container,
        video_channel=0,
    )

    # Verify all frames were created
    assert len(frame_sample_ids) == 2

    # Verify frames are in the database
    video_frames = video_frame_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=video_frames_collection_id,
    ).samples
    assert len(video_frames) == 2

    # Verify frame properties
    assert video_frames[0].frame_number == 0
    assert video_frames[0].parent_sample_id == video_sample_id
    assert video_frames[0].frame_timestamp_s == 0
    assert video_frames[1].frame_number == 1
    assert video_frames[1].parent_sample_id == video_sample_id
    assert video_frames[1].frame_timestamp_s == 1
    video_container.close()
    video_file.close()


def test__configure_stream_threading__with_explicit_thread_count() -> None:
    """Test configuring threading with explicit thread count."""
    video_stream = MagicMock()

    add_videos._configure_stream_threading(video_stream=video_stream, num_decode_threads=4)

    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 4


def test__configure_stream_threading__auto_calculate_threads(mocker: MockerFixture) -> None:
    """Test automatic thread count calculation based on CPU count."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=8)
    add_videos._configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should use cpu_count - 1 = 7
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 7


def test__configure_stream_threading__capped_at_16_threads(mocker: MockerFixture) -> None:
    """Test that thread count is capped at 16."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=32)
    add_videos._configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should be capped at 16
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 16


def test__configure_stream_threading__min_1_thread(mocker: MockerFixture) -> None:
    """Test that at least 1 thread is used even with single CPU."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=1)
    add_videos._configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should use at least 1
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 1


def test_load_video_annotations_from_labelformat(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Arrange
    create_video_file(
        output_path=tmp_path / "video_1.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )

    categories = [Category(id=0, name="cat"), Category(id=1, name="dog")]
    video_annotation = _get_object_detection_track(
        filename=str(tmp_path / "video_1"),
        number_of_frames=2,
        categories=categories,
        boxes_by_object=[
            [[1.0, 2.0, 3.0, 4.0], None],
            [None, [5.0, 6.0, 7.0, 8.0]],
        ],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation],
    )

    video_paths = video_dataset._collect_video_file_paths(path=tmp_path)

    # Act
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    _, frame_sample_ids = add_videos.load_video_annotations_from_labelformat(
        session=db_session,
        dataset_id=collection.collection_id,
        video_paths=video_paths,
        input_labels=input_labels,
        input_labels_paths_root=tmp_path,
    )

    # Assert
    annotations = annotation_resolver.get_all(db_session).annotations
    assert len(annotations) == 2
    assert {annotations[0].parent_sample_id, annotations[1].parent_sample_id} == set(
        frame_sample_ids
    )

    # Check annotation content
    assert annotations[0].annotation_type == "object_detection"
    assert annotations[0].annotation_label.annotation_label_name == "cat"
    assert annotations[1].annotation_type == "object_detection"
    assert annotations[1].annotation_label.annotation_label_name == "dog"


def test_load_video_annotations_from_labelformat__multiple_videos(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Arrange
    create_video_file(
        output_path=tmp_path / "video_1.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )
    create_video_file(
        output_path=tmp_path / "video_2.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )

    categories = [Category(id=0, name="cat"), Category(id=1, name="dog")]
    video_annotation_1 = _get_object_detection_track(
        filename=str(tmp_path / "video_1"),
        number_of_frames=2,
        categories=categories,
        boxes_by_object=[
            [[1.0, 2.0, 3.0, 4.0], None],
            [None, [5.0, 6.0, 7.0, 8.0]],
        ],
    )
    video_annotation_2 = _get_object_detection_track(
        filename=str(tmp_path / "video_2"),
        number_of_frames=2,
        categories=categories,
        boxes_by_object=[
            [[10.0, 20.0, 30.0, 40.0], [11.0, 21.0, 31.0, 41.0]],
            [[50.0, 60.0, 70.0, 80.0], None],
        ],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation_1, video_annotation_2],
    )

    video_paths = video_dataset._collect_video_file_paths(path=tmp_path)

    # Act
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    add_videos.load_video_annotations_from_labelformat(
        session=db_session,
        dataset_id=collection.collection_id,
        video_paths=video_paths,
        input_labels=input_labels,
        input_labels_paths_root=tmp_path,
    )

    # Assert
    annotations = annotation_resolver.get_all(db_session).annotations
    assert len(annotations) == 5  # 2 from video_1, 3 from video_2

    # Check annotation content
    assert all(a.annotation_type == "object_detection" for a in annotations)
    label_names = {a.annotation_label.annotation_label_name for a in annotations}
    assert label_names == {"cat", "dog"}


def test_load_video_annotations_from_labelformat__same_name_in_different_folders(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Arrange
    first_dir = tmp_path / "dir_1"
    second_dir = tmp_path / "dir_2"
    first_dir.mkdir()
    second_dir.mkdir()

    create_video_file(
        output_path=first_dir / "video.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )
    create_video_file(
        output_path=second_dir / "video.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )

    categories = [Category(id=0, name="cat")]
    video_annotation_1 = _get_object_detection_track(
        filename="dir_1/video",
        number_of_frames=2,
        categories=categories,
        boxes_by_object=[[[1.0, 2.0, 3.0, 4.0], None]],
    )
    video_annotation_2 = _get_object_detection_track(
        filename="dir_2/video",
        number_of_frames=2,
        categories=categories,
        boxes_by_object=[[[5.0, 6.0, 7.0, 8.0], None]],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation_1, video_annotation_2],
    )
    video_paths = video_dataset._collect_video_file_paths(path=tmp_path)

    # Act
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    created_video_sample_ids, _ = add_videos.load_video_annotations_from_labelformat(
        session=db_session,
        dataset_id=collection.collection_id,
        video_paths=video_paths,
        input_labels=input_labels,
        input_labels_paths_root=tmp_path,
    )

    # Assert
    assert len(created_video_sample_ids) == 2
    videos = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
    ).samples
    assert len(videos) == 2


def test_resolve_video_paths_from_labelformat__same_name_in_different_folders(
    tmp_path: Path,
) -> None:
    video_paths = [
        str(tmp_path / "dir_1" / "video.mp4"),
        str(tmp_path / "dir_2" / "video.mp4"),
        str(
            tmp_path / "dir_2" / "video1.mp4"
        ),  # This should not appear as it is not in the labels.
    ]
    categories = [Category(id=0, name="cat")]
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[
            _get_object_detection_track(
                filename="dir_1/video",
                number_of_frames=1,
                categories=categories,
                boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
            ),
            _get_object_detection_track(
                filename="dir_2/video",
                number_of_frames=1,
                categories=categories,
                boxes_by_object=[[[5.0, 6.0, 7.0, 8.0]]],
            ),
        ],
    )

    resolved_paths = add_videos._resolve_video_paths_from_labelformat(
        input_labels=input_labels,
        root_path=tmp_path,
        video_paths=video_paths,
    )

    assert len(resolved_paths) == 2
    assert set(resolved_paths) == {
        str(tmp_path / "dir_1" / "video.mp4"),
        str(tmp_path / "dir_2" / "video.mp4"),
    }


def test_resolve_video_paths_from_labelformat__raises_on_duplicate_path_without_suffix(
    tmp_path: Path,
) -> None:
    categories = [Category(id=0, name="cat")]
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[
            _get_object_detection_track(
                filename="dir_1/video",
                number_of_frames=1,
                categories=categories,
                boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
            )
        ],
    )

    with pytest.raises(ValueError, match="Duplicate video path"):
        add_videos._resolve_video_paths_from_labelformat(
            input_labels=input_labels,
            root_path=tmp_path,
            video_paths=[
                str(tmp_path / "dir_1" / "video.mp4"),
                str(tmp_path / "dir_1" / "video.mov"),
            ],
        )


def test_resolve_video_paths_from_labelformat__prefers_explicit_extension(
    tmp_path: Path,
) -> None:
    categories = [Category(id=0, name="cat")]
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[
            _get_object_detection_track(
                filename="dir_1/video.mp4",
                number_of_frames=1,
                categories=categories,
                boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
            )
        ],
    )

    resolved_paths = add_videos._resolve_video_paths_from_labelformat(
        input_labels=input_labels,
        root_path=tmp_path,
        video_paths=[
            str(tmp_path / "dir_1" / "video.mov"),
        ],
    )

    assert resolved_paths == [str(tmp_path / "dir_1" / "video.mp4")]


def test_load_video_annotations_from_labelformat__raises_on_frame_mismatch(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Arrange - create video with 2 frames but annotation says 1 frame
    create_video_file(
        output_path=tmp_path / "video_2.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )
    categories = [Category(id=0, name="cat")]
    video_annotation = _get_object_detection_track(
        filename=str(tmp_path / "video_2"),
        number_of_frames=1,
        categories=categories,
        boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation],
    )

    video_paths = video_dataset._collect_video_file_paths(path=tmp_path)

    # Act / Assert
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    with pytest.raises(ValueError, match="Number of frames in annotation"):
        add_videos.load_video_annotations_from_labelformat(
            session=db_session,
            dataset_id=collection.collection_id,
            video_paths=video_paths,
            input_labels=input_labels,
            input_labels_paths_root=tmp_path,
        )


def test_load_video_annotations_from_labelformat__raises_on_missing_video(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Arrange - create video_3.mp4 but annotation references missing_video
    create_video_file(
        output_path=tmp_path / "video_3.mp4",
        width=640,
        height=480,
        num_frames=2,
        fps=2,
    )
    categories = [Category(id=0, name="cat")]
    video_annotation = _get_object_detection_track(
        filename=str(tmp_path / "missing_video"),
        number_of_frames=1,
        categories=categories,
        boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation],
    )

    video_paths = video_dataset._collect_video_file_paths(path=tmp_path)

    # Act / Assert
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    with pytest.raises(FileNotFoundError, match="No video file found"):
        add_videos.load_video_annotations_from_labelformat(
            session=db_session,
            dataset_id=collection.collection_id,
            video_paths=video_paths,
            input_labels=input_labels,
            input_labels_paths_root=tmp_path,
        )


def test_process_video_annotations_object_detection() -> None:
    # Arrange
    frame_number_to_id = {0: uuid4(), 1: uuid4()}
    label_map = {0: uuid4(), 1: uuid4()}
    categories = [Category(id=0, name="cat"), Category(id=1, name="dog")]
    video_annotation = _get_object_detection_track(
        filename="video",
        number_of_frames=2,
        categories=categories,
        boxes_by_object=[
            [[0.0, 1.0, 2.0, 3.0], None],
            [None, [4.0, 5.0, 6.0, 7.0]],
        ],
    )
    # Create object track map with one track for each object
    object_track_map = {
        0: uuid4(),
        1: uuid4(),
    }

    # Act
    annotations = add_videos._process_video_annotations_object_detection(
        frame_number_to_id=frame_number_to_id,
        video_annotation=video_annotation,
        label_map=label_map,
        object_track_map=object_track_map,
    )

    # Assert
    assert len(annotations) == 2
    assert annotations[0].parent_sample_id == frame_number_to_id[0]
    assert annotations[0].annotation_label_id == label_map[0]
    assert annotations[0].annotation_type == "object_detection"
    assert annotations[0].x == 0
    assert annotations[0].y == 1
    assert annotations[0].width == 2
    assert annotations[0].height == 3
    assert annotations[0].object_track_id == object_track_map[0]
    assert annotations[1].parent_sample_id == frame_number_to_id[1]
    assert annotations[1].annotation_label_id == label_map[1]
    assert annotations[1].object_track_id == object_track_map[1]


def test_process_video_annotations_instance_segmentation() -> None:
    # Arrange
    frame_number_to_id = {0: uuid4(), 1: uuid4()}
    label_map = {0: uuid4(), 1: uuid4()}
    categories = [Category(id=0, name="cat"), Category(id=1, name="dog")]
    video_annotation = _get_instance_segmentation_track(
        filename="video",
        number_of_frames=2,
        categories=categories,
        segmentations_by_object=[
            [
                MultiPolygon(polygons=[[(1.0, 2.0), (4.0, 2.0), (4.0, 5.0), (1.0, 5.0)]]),
                MultiPolygon(polygons=[[(1.0, 2.0), (4.0, 2.0), (4.0, 5.0), (1.0, 5.0)]]),
            ],
            [
                None,
                MultiPolygon(polygons=[[(1.0, 2.0), (4.0, 2.0), (4.0, 5.0), (1.0, 5.0)]]),
            ],
        ],
    )
    # Create object track map with one track for the second object and no track for the first object
    object_track_map = {
        1: uuid4(),
    }

    # Act
    annotations = add_videos._process_video_annotations_instance_segmentation(
        frame_number_to_id=frame_number_to_id,
        video_annotation=video_annotation,
        label_map=label_map,
        object_track_map=object_track_map,
    )

    # Assert
    assert len(annotations) == 3
    assert annotations[0].annotation_type == "instance_segmentation"
    assert annotations[0].segmentation_mask is None
    assert annotations[0].annotation_label_id == label_map[0]
    assert annotations[0].parent_sample_id == frame_number_to_id[0]
    assert annotations[0].object_track_id is None  # No track for first object
    assert annotations[1].annotation_type == "instance_segmentation"
    assert annotations[1].segmentation_mask is None
    assert annotations[1].annotation_label_id == label_map[0]
    assert annotations[1].parent_sample_id == frame_number_to_id[1]
    assert annotations[1].object_track_id is None  # No track for first object
    assert annotations[2].annotation_type == "instance_segmentation"
    assert annotations[2].segmentation_mask is None
    assert annotations[2].annotation_label_id == label_map[1]
    assert annotations[2].parent_sample_id == frame_number_to_id[1]
    assert annotations[2].object_track_id == object_track_map[1]


class _ObjectDetectionTrackInput(ObjectDetectionTrackInput):
    def __init__(
        self,
        categories: list[Category],
        video_annotations: list[VideoObjectDetectionTrack],
    ) -> None:
        self._categories = categories
        self._video_annotations = video_annotations

    def get_categories(self) -> list[Category]:
        return self._categories

    def get_labels(self) -> list[VideoObjectDetectionTrack]:
        return self._video_annotations

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        pass

    def get_videos(self) -> list[Video]:
        return list({annotation.video for annotation in self._video_annotations})


def _get_object_detection_track(
    filename: str,
    number_of_frames: int,
    categories: list[Category],
    boxes_by_object: list[list[list[float] | None]],
) -> VideoObjectDetectionTrack:
    objects = [
        SingleObjectDetectionTrack(
            category=category,
            boxes=[
                BoundingBox.from_format(bbox=box, format=BoundingBoxFormat.XYWH)
                if box is not None
                else None
                for box in boxes
            ],
        )
        for category, boxes in zip(categories, boxes_by_object)
    ]
    return VideoObjectDetectionTrack(
        video=Video(
            id=0,
            filename=filename,
            width=640,
            height=480,
            number_of_frames=number_of_frames,
        ),
        objects=objects,
    )


def _get_instance_segmentation_track(
    filename: str,
    number_of_frames: int,
    categories: list[Category],
    segmentations_by_object: list[list[MultiPolygon | BinaryMaskSegmentation | None]],
) -> VideoInstanceSegmentationTrack:
    objects = [
        SingleInstanceSegmentationTrack(
            category=category,
            segmentations=segmentations,
        )
        for category, segmentations in zip(categories, segmentations_by_object)
    ]
    return VideoInstanceSegmentationTrack(
        video=Video(
            id=0,
            filename=filename,
            width=640,
            height=480,
            number_of_frames=number_of_frames,
        ),
        objects=objects,
    )
