"""Functions to add videos to a dataset in the database."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, cast
from uuid import UUID

import av
import fsspec
import numpy as np
from av import FFmpegError, container
from av.codec.context import ThreadType
from av.container import InputContainer
from av.video.frame import VideoFrame as AVVideoFrame
from av.video.stream import VideoStream
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core import loading_log
from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    collection_resolver,
    sample_resolver,
    video_frame_resolver,
    video_resolver,
)

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_CHANNEL = 0
# Number of samples to process in a single batch
SAMPLE_BATCH_SIZE = 128

# Video file extensions
# These are commonly supported by PyAV/FFmpeg.
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
}


@dataclass
class FrameExtractionContext:
    """Lightweight container for the metadata needed during frame extraction."""

    session: Session
    collection_id: UUID
    video_sample_id: UUID


def load_into_dataset_from_paths(
    session: Session,
    dataset_id: UUID,
    video_paths: Iterable[str],
    video_channel: int = DEFAULT_VIDEO_CHANNEL,
    num_decode_threads: int | None = None,
) -> tuple[list[UUID], list[UUID]]:
    """Load video samples from file paths into the dataset using PyAV.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load video samples into. It should have
        sample_type == SampleType.VIDEO.
        video_paths: An iterable of file paths to the videos to load.
        video_channel: The video channel from which frames are loaded.
        num_decode_threads: Optional override for the number of FFmpeg decode threads.
            If omitted, the available CPU cores - 1 (max 16) are used.

    Returns:
        A tuple containing:
            - List of UUIDs of the created video samples
            - List of UUIDs of the created video frame samples
    """
    created_video_sample_ids: list[UUID] = []
    created_video_frame_sample_ids: list[UUID] = []
    video_paths_list = list(video_paths)
    file_paths_new, file_paths_exist = video_resolver.filter_new_paths(
        session=session, file_paths_abs=video_paths_list
    )
    video_logging_context = loading_log.LoadingLoggingContext(
        n_samples_to_be_inserted=len(video_paths_list),
        n_samples_before_loading=sample_resolver.count_by_collection_id(
            session=session, collection_id=dataset_id
        ),
    )
    video_logging_context.update_example_paths(file_paths_exist)
    # Get the video frames dataset ID
    video_frames_dataset_id = collection_resolver.get_or_create_child_collection(
        session=session, collection_id=dataset_id, sample_type=SampleType.VIDEO_FRAME
    )

    for video_path in tqdm(
        file_paths_new,
        desc="Loading frames from videos",
        unit=" video",
    ):
        try:
            # Open video and extract metadata
            fs, fs_path = fsspec.core.url_to_fs(url=video_path)
            video_file = fs.open(path=fs_path, mode="rb")
            try:
                # Open video container for reading (returns InputContainer)
                video_container = container.open(file=video_file)
                video_stream = video_container.streams.video[video_channel]

                # Get video metadata
                framerate = float(video_stream.average_rate) or 0.0
                video_width = video_stream.width or 0
                video_height = video_stream.height or 0
                if video_stream.duration and video_stream.time_base:
                    video_duration = float(video_stream.duration * video_stream.time_base)
                else:
                    video_duration = None

                # Create video sample
                video_sample_ids = video_resolver.create_many(
                    session=session,
                    collection_id=dataset_id,
                    samples=[
                        VideoCreate(
                            file_path_abs=video_path,
                            width=video_width,
                            height=video_height,
                            duration_s=video_duration,
                            fps=framerate,
                            file_name=Path(video_path).name,
                        )
                    ],
                )

                if len(video_sample_ids) != 1:
                    video_container.close()
                    raise (RuntimeError(f"There was an error adding {video_path} to the dataset."))
                created_video_sample_ids.append(video_sample_ids[0])

                # Create video frame samples by parsing all frames
                extraction_context = FrameExtractionContext(
                    session=session,
                    collection_id=video_frames_dataset_id,
                    video_sample_id=video_sample_ids[0],
                )
                frame_sample_ids = _create_video_frame_samples(
                    context=extraction_context,
                    video_container=video_container,
                    video_channel=video_channel,
                    num_decode_threads=num_decode_threads,
                )
                created_video_frame_sample_ids.extend(frame_sample_ids)

                video_container.close()
            finally:
                # Ensure file is closed even if container operations fail
                video_file.close()

        except (FileNotFoundError, OSError, IndexError, FFmpegError) as e:
            logger.error(f"Error processing video {video_path}: {e}")
            continue

    loading_log.log_loading_results(
        session=session, dataset_id=dataset_id, logging_context=video_logging_context
    )

    return created_video_sample_ids, created_video_frame_sample_ids


def _create_video_frame_samples(
    context: FrameExtractionContext,
    video_container: InputContainer,
    video_channel: int,
    num_decode_threads: int | None = None,
) -> list[UUID]:
    """Create video frame samples for a video by parsing all frames.

    This function decodes all frames to extract metadata.

    Args:
        context: Frame extraction context (session, dataset and parent video).
        video_container: The PyAV container with the opened video.
        video_channel: The video channel from which frames are loaded.
        num_decode_threads: Optional override for FFmpeg decode thread count.

    Returns:
        A list of UUIDs of the created video frame samples.
    """
    created_sample_ids: list[UUID] = []
    samples_to_create: list[VideoFrameCreate] = []
    video_stream = video_container.streams.video[video_channel]
    _configure_stream_threading(video_stream=video_stream, num_decode_threads=num_decode_threads)

    # Get time base for converting PTS to seconds
    time_base = video_stream.time_base if video_stream.time_base else None

    # Decode all frames
    for decoded_index, frame in enumerate(video_container.decode(video_stream)):
        # Get the presentation timestamp in seconds from the frame
        # Convert frame.pts from time base units to seconds
        if frame.pts is not None and time_base is not None:
            frame_timestamp_s = float(frame.pts * time_base)
        else:
            # Fallback to frame.time if pts or time_base is not available
            frame_timestamp_s = frame.time if frame.time is not None else -1.0

        sample = VideoFrameCreate(
            frame_number=decoded_index,
            frame_timestamp_s=frame_timestamp_s,
            frame_timestamp_pts=frame.pts if frame.pts is not None else -1,
            parent_sample_id=context.video_sample_id,
            rotation_deg=_get_frame_rotation_deg(frame=frame),
        )
        samples_to_create.append(sample)

        # Process batch when it reaches SAMPLE_BATCH_SIZE
        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_samples_batch = video_frame_resolver.create_many(
                session=context.session,
                samples=samples_to_create,
                collection_id=context.collection_id,
            )
            created_sample_ids.extend(created_samples_batch)
            samples_to_create = []

    # Handle remaining samples for this video
    if samples_to_create:
        created_samples_batch = video_frame_resolver.create_many(
            session=context.session,
            samples=samples_to_create,
            collection_id=context.collection_id,
        )
        created_sample_ids.extend(created_samples_batch)

    return created_sample_ids


def _configure_stream_threading(video_stream: VideoStream, num_decode_threads: int | None) -> None:
    """Configure codec-level threading for faster decode when available."""
    codec_context = getattr(video_stream, "codec_context", None)
    if codec_context is None:
        return

    if num_decode_threads is None:
        cpu_count = os.cpu_count() or 1
        # Use available cores - 1 but at least 1. Cap to prevent runaway usage.
        num_decode_threads = max(1, min(cpu_count - 1 or 1, 16))

    try:
        codec_context.thread_type = ThreadType.AUTO
        codec_context.thread_count = num_decode_threads
    except av.AVError:
        # Some codecs do not support threading—ignore silently.
        logger.warning(
            "Could not set up multithreading to decode videos, will use a single thread."
        )


def _get_frame_rotation_deg(frame: AVVideoFrame) -> int:
    """Get the rotation metadata from a video frame.

    Reads DISPLAYMATRIX side data to determine rotation.

    Args:
        frame: A decoded video frame.

    Returns:
        The rotation in degrees. Valid values are 0, 90, 180, 270.
    """
    matrix_data = frame.side_data.get("DISPLAYMATRIX")
    if matrix_data is None:
        return 0
    buffer = cast(bytes, matrix_data)
    matrix = np.frombuffer(buffer=buffer, dtype=np.int32).reshape((3, 3))

    # The top left 2x2 sub-matrix has four possible configurations. The rotation can be
    # determined from the first two values.
    #
    #  0        90       180      270
    #  x  0     0 -x    -x  0     0  x
    #  0  x     x  0     0 -x    -x  0
    if matrix[0, 0] > 0:
        return 0
    if matrix[0, 0] < 0:
        return 180
    if matrix[0, 1] < 0:
        return 90
    return 270
