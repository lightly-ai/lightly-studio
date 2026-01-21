from __future__ import annotations

import os
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import av
import fsspec
import numpy as np
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
from PIL import Image as PILImage
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core import add_videos
from lightly_studio.core.add_videos import (
    FrameExtractionContext,
    _configure_stream_threading,
    _create_label_map,
    _create_video_frame_samples,
    _process_video_annotations_instance_segmentation,
    _process_video_annotations_object_detection,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    video_frame_resolver,
    video_resolver,
)
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_load_into_collection_from_paths(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    # Create two temporary video files.
    first_video_path = _create_temp_video(
        output_path=tmp_path / "test_video_1.mp4",
        width=640,
        height=480,
        num_frames=30,
        fps=2,
    )
    second_video_path = _create_temp_video(
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
    video_path = _create_temp_video(
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

    frame_sample_ids = _create_video_frame_samples(
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


def _create_temp_video(
    output_path: Path,
    width: int = 640,
    height: int = 480,
    num_frames: int = 30,
    fps: int = 30,
) -> Path:
    """Create a temporary video file using PyAV for testing.

    Args:
        output_path: Path where the video file will be saved.
        width: Width of the video in pixels.
        height: Height of the video in pixels.
        num_frames: Number of frames to generate.
        fps: Frame rate of the video.

    Returns:
        The path to the created video file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Open output container
    output_container = av.open(str(output_path), mode="w")  # type: ignore[attr-defined]

    # Add video stream
    stream = output_container.add_stream("libx264", rate=fps)
    stream.width = width  # type: ignore[attr-defined]
    stream.height = height  # type: ignore[attr-defined]
    stream.pix_fmt = "yuv420p"  # type: ignore[attr-defined]

    # Generate simple solid color frames
    frame_data = np.zeros((height, width, 3), dtype=np.uint8)
    pil_image = PILImage.fromarray(frame_data, "RGB")

    for frame_num in range(num_frames):
        # Convert PIL Image to PyAV frame
        av_frame = av.VideoFrame.from_image(pil_image)  # type: ignore[attr-defined]
        av_frame.pts = frame_num
        if stream.time_base is not None:
            av_frame.time_base = stream.time_base

        # Encode and mux the frame
        for packet in stream.encode(av_frame):  # type: ignore[attr-defined]
            output_container.mux(packet)

    # Flush the encoder
    for packet in stream.encode():  # type: ignore[attr-defined]
        output_container.mux(packet)

    # Close the container
    output_container.close()

    return output_path


def test__configure_stream_threading__with_explicit_thread_count() -> None:
    """Test configuring threading with explicit thread count."""
    video_stream = MagicMock()

    _configure_stream_threading(video_stream=video_stream, num_decode_threads=4)

    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 4


def test__configure_stream_threading__auto_calculate_threads(mocker: MockerFixture) -> None:
    """Test automatic thread count calculation based on CPU count."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=8)
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should use cpu_count - 1 = 7
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 7


def test__configure_stream_threading__capped_at_16_threads(mocker: MockerFixture) -> None:
    """Test that thread count is capped at 16."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=32)
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should be capped at 16
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 16


def test__configure_stream_threading__min_1_thread(mocker: MockerFixture) -> None:
    """Test that at least 1 thread is used even with single CPU."""
    video_stream = MagicMock()

    mocker.patch.object(os, "cpu_count", return_value=1)
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=None)

    # Should use at least 1
    assert video_stream.codec_context.thread_type == ThreadType.AUTO
    assert video_stream.codec_context.thread_count == 1


def test_create_label_map(db_session: Session) -> None:
    # Arrange
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    input_labels = _ObjectDetectionTrackInput(
        categories=[Category(id=0, name="cat"), Category(id=1, name="dog")],
        video_annotations=[],
    )

    # Act
    label_map_first = _create_label_map(
        session=db_session,
        dataset_id=collection.collection_id,
        input_labels=input_labels,
    )

    input_labels_updated = _ObjectDetectionTrackInput(
        categories=[
            Category(id=0, name="cat"),
            Category(id=1, name="dog"),
            Category(id=2, name="bird"),
        ],
        video_annotations=[],
    )

    # Act
    label_map_second = _create_label_map(
        session=db_session,
        dataset_id=collection.collection_id,
        input_labels=input_labels_updated,
    )

    # Assert
    assert label_map_second[0] == label_map_first[0]
    assert label_map_second[1] == label_map_first[1]
    assert label_map_second[2] not in label_map_first.values()


def test_process_video_annotations_object_detection() -> None:
    # Arrange
    frames_collection_id = uuid4()
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

    # Act
    annotations = _process_video_annotations_object_detection(
        frames_collection_id=frames_collection_id,
        frame_number_to_id=frame_number_to_id,
        video_annotation=video_annotation,
        label_map=label_map,
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
    assert annotations[1].parent_sample_id == frame_number_to_id[1]
    assert annotations[1].annotation_label_id == label_map[1]


def test_process_video_annotations_instance_segmentation() -> None:
    # Arrange
    frames_collection_id = uuid4()
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

    # Act
    annotations = _process_video_annotations_instance_segmentation(
        frames_collection_id=frames_collection_id,
        frame_number_to_id=frame_number_to_id,
        video_annotation=video_annotation,
        label_map=label_map,
    )

    # Assert
    assert len(annotations) == 3
    assert annotations[0].annotation_type == "instance_segmentation"
    assert annotations[0].segmentation_mask is None
    assert annotations[0].annotation_label_id == label_map[0]
    assert annotations[0].parent_sample_id == frame_number_to_id[0]
    assert annotations[1].annotation_type == "instance_segmentation"
    assert annotations[1].segmentation_mask is None
    assert annotations[1].annotation_label_id == label_map[0]
    assert annotations[1].parent_sample_id == frame_number_to_id[1]
    assert annotations[2].annotation_type == "instance_segmentation"
    assert annotations[2].segmentation_mask is None
    assert annotations[2].annotation_label_id == label_map[1]
    assert annotations[2].parent_sample_id == frame_number_to_id[1]


def test_load_video_annotations_from_labelformat(
    db_session: Session,
) -> None:
    # Arrange
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    video_frames_data = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video_1.mp4", duration_s=1.0, fps=2.0),
    )
    categories = [Category(id=0, name="cat"), Category(id=1, name="dog")]
    video_annotation = _get_object_detection_track(
        filename="video_1",
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

    # Act
    add_videos.load_video_annotations_from_labelformat(
        session=db_session,
        dataset_id=collection.collection_id,
        input_labels=input_labels,
    )

    # Assert
    annotations = annotation_resolver.get_all(db_session).annotations
    assert len(annotations) == 2
    frame_ids = set(video_frames_data.frame_sample_ids)
    assert {annotations[0].parent_sample_id, annotations[1].parent_sample_id} == frame_ids


def test_load_video_annotations_from_labelformat__raises_on_frame_mismatch(
    db_session: Session,
) -> None:
    # Arrange
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video_2.mp4", duration_s=1.0, fps=2.0),
    )
    categories = [Category(id=0, name="cat")]
    video_annotation = _get_object_detection_track(
        filename="video_2",
        number_of_frames=1,
        categories=categories,
        boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation],
    )

    # Act / Assert
    with pytest.raises(ValueError, match="Number of frames in annotation"):
        add_videos.load_video_annotations_from_labelformat(
            session=db_session,
            dataset_id=collection.collection_id,
            input_labels=input_labels,
        )


def test_load_video_annotations_from_labelformat__raises_on_missing_video(
    db_session: Session,
) -> None:
    # Arrange
    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video_3.mp4", duration_s=1.0, fps=2.0),
    )
    categories = [Category(id=0, name="cat")]
    video_annotation = _get_object_detection_track(
        filename="missing_video",
        number_of_frames=1,
        categories=categories,
        boxes_by_object=[[[1.0, 2.0, 3.0, 4.0]]],
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation],
    )

    # Act / Assert
    with pytest.raises(KeyError):
        add_videos.load_video_annotations_from_labelformat(
            session=db_session,
            dataset_id=collection.collection_id,
            input_labels=input_labels,
        )


def test_load_video_annotations_from_labelformat__raises_on_unsupported_type(
    db_session: Session,
) -> None:
    # Arrange
    class UnsupportedTrack:
        def __init__(self, video: Video) -> None:
            self.video = video

    collection = create_collection(db_session, sample_type=SampleType.VIDEO)
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video_4.mp4", duration_s=1.0, fps=2.0),
    )
    categories = [Category(id=0, name="cat")]
    video_annotation = UnsupportedTrack(
        video=Video(id=0, filename="video_4", width=640, height=480, number_of_frames=2),
    )
    input_labels = _ObjectDetectionTrackInput(
        categories=categories,
        video_annotations=[video_annotation],  # type: ignore[list-item]
    )

    # Act / Assert
    with pytest.raises(ValueError, match="Unsupported annotation type"):
        add_videos.load_video_annotations_from_labelformat(
            session=db_session,
            dataset_id=collection.collection_id,
            input_labels=input_labels,
        )


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
        return []


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
