"""Functions to add videos to a dataset in the database."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from uuid import UUID

import av
import fsspec
from av import container
from av.container import InputContainer
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core import logging
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    dataset_resolver,
    sample_resolver,
    video_frame_resolver,
    video_resolver,
)

DEFAULT_VIDEO_CHANNEL = 0
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch

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


def load_into_dataset_from_paths(
    session: Session,
    dataset_id: UUID,
    video_paths: Iterable[str],
    video_channel: int = DEFAULT_VIDEO_CHANNEL,
) -> tuple[list[UUID], list[UUID]]:
    """Load video samples from file paths into the dataset using PyAV.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load video samples into. It should have
        sample_type == SampleType.VIDEO.
        video_paths: An iterable of file paths to the videos to load.
        video_channel: The video channel from which frames are loaded.

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
    video_logging_context = logging.LoadingLoggingContext(
        n_samples_to_be_inserted=len(video_paths_list),
        n_samples_before_loading=sample_resolver.count_by_dataset_id(
            session=session, dataset_id=dataset_id
        ),
    )
    video_logging_context.update_example_paths(file_paths_exist)
    # Get the video frames dataset ID
    video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=session, dataset_id=dataset_id
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
                    dataset_id=dataset_id,
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
                frame_sample_ids = _create_video_frame_samples(
                    session=session,
                    dataset_id=video_frames_dataset_id,
                    video_sample_id=video_sample_ids[0],
                    video_container=video_container,
                    video_channel=video_channel,
                )
                created_video_frame_sample_ids.extend(frame_sample_ids)

                video_container.close()
            finally:
                # Ensure file is closed even if container operations fail
                video_file.close()

        except (FileNotFoundError, OSError, IndexError, av.AVError) as e:
            print(f"Error processing video {video_path}: {e}")
            continue

    logging.log_loading_results(
        session=session, dataset_id=dataset_id, logging_context=video_logging_context
    )
    return created_video_sample_ids, created_video_frame_sample_ids


def _create_video_frame_samples(
    session: Session,
    dataset_id: UUID,
    video_sample_id: UUID,
    video_container: InputContainer,
    video_channel: int,
) -> list[UUID]:
    """Create video frame samples for a video by parsing all frames.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load video frames into.
        video_sample_id: The ID of the video sample to create frames for.
        video_container: The PyAV container with the opened video.
        video_channel: The video channel from which frames are loaded.

    Returns:
        A list of UUIDs of the created video frame samples.
    """
    created_sample_ids: list[UUID] = []
    samples_to_create: list[VideoFrameCreate] = []
    video_stream = video_container.streams.video[video_channel]

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
            parent_sample_id=video_sample_id,
        )
        samples_to_create.append(sample)

        # Process batch when it reaches SAMPLE_BATCH_SIZE
        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_samples_batch = video_frame_resolver.create_many(
                session=session,
                samples=samples_to_create,
                dataset_id=dataset_id,
            )
            created_sample_ids.extend(created_samples_batch)
            samples_to_create = []

    # Handle remaining samples for this video
    if samples_to_create:
        created_samples_batch = video_frame_resolver.create_many(
            session=session,
            samples=samples_to_create,
            dataset_id=dataset_id,
        )
        created_sample_ids.extend(created_samples_batch)

    return created_sample_ids
