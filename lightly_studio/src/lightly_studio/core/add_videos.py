"""Functions to add videos to a dataset in the database."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from uuid import UUID

import av
import fsspec
from av import container
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.logging import LoadingLoggingContext, log_loading_results
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    dataset_resolver,
    sample_resolver,
    video_frame_resolver,
    video_resolver,
)

DEFAULT_VIDEO_CHANNEL = 0
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


def load_into_dataset_from_paths(
    session: Session,
    dataset_id: UUID,
    video_paths: Iterable[str],
    video_channel: int = DEFAULT_VIDEO_CHANNEL,
    fps: float | None = None,
) -> list[UUID]:
    """Load video frames from file paths into the dataset using PyAV.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load video frames into.
        video_paths: An iterable of file paths to the videos to load.
        video_channel: The video channel from which frames are loaded.
        fps: Optional FPS value to control frame extraction. If provided, only frames
            at the specified FPS intervals will be extracted. If None, all frames
            will be extracted.

    Returns:
        A list of UUIDs of the created samples.
    """
    created_sample_ids: list[UUID] = []
    file_paths_new, file_paths_exist = video_resolver.filter_new_paths(
        session=session, file_paths_abs=list(video_paths)
    )
    video_logging_context = LoadingLoggingContext(
        n_samples_to_be_inserted=sum(1 for _ in video_paths),
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
        desc="Loading videos",
        unit=" videos",
    ):
        try:
            # Open video and extract metadata
            fs, fs_path = fsspec.core.url_to_fs(url=video_path)
            video_file = fs.open(fs_path, "rb")
            try:
                # Open video container for reading (returns InputContainer)
                video_container: av.container.InputContainer = container.open(
                    video_file,
                )
                video_stream = video_container.streams.video[video_channel]

                # Get video metadata
                framerate = float(video_stream.average_rate) if video_stream.average_rate else 0.0
                video_width = video_stream.width if video_stream.width else 0
                video_height = video_stream.height if video_stream.height else 0
                if video_stream.duration and video_stream.time_base:
                    video_duration = float(video_stream.duration * video_stream.time_base)
                else:
                    video_duration = 0.0

                # Create video sample
                video_sample_ids = video_resolver.create_many(
                    session=session,
                    dataset_id=dataset_id,
                    samples=[
                        VideoCreate(
                            file_path_abs=video_path,
                            width=video_width,
                            height=video_height,
                            duration_s=float(video_duration),
                            fps=framerate,
                            file_name=Path(video_path).name,
                        )
                    ],
                )

                if not video_sample_ids:
                    video_container.close()
                    continue

                # Create video frame samples by parsing all frames
                frame_sample_ids = _create_video_frame_samples(
                    session=session,
                    dataset_id=video_frames_dataset_id,
                    video_sample_id=video_sample_ids[0],
                    video_container=video_container,
                    video_stream=video_stream,
                    fps=fps,
                )
                created_sample_ids.extend(frame_sample_ids)

                video_container.close()
            finally:
                # Ensure file is closed even if container operations fail
                video_file.close()

        except (FileNotFoundError, OSError, IndexError, av.AVError) as e:
            print(f"Error processing video {video_path}: {e}")
            continue

    log_loading_results(
        session=session, dataset_id=dataset_id, logging_context=video_logging_context
    )
    return created_sample_ids


def _create_video_frame_samples(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    video_sample_id: UUID,
    video_container: av.container.InputContainer,
    video_stream: av.video.stream.VideoStream,
    fps: float | None = None,
) -> list[UUID]:
    """Create video frame samples for a video by parsing all frames.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load video frames into.
        video_sample_id: The ID of the video sample to create frames for.
        video_container: The PyAV container with the opened video.
        video_stream: The video stream from the container.
        fps: Optional FPS value to control frame extraction. If provided, only frames
            at the specified FPS intervals will be extracted. If None, all frames
            will be extracted.

    Returns:
        A list of UUIDs of the created video frame samples.
    """
    created_sample_ids: list[UUID] = []
    samples_to_create: list[VideoFrameCreate] = []

    # Calculate minimum time interval between frames if fps is specified
    min_time_interval = 1.0 / fps if fps is not None and fps > 0 else 0.0
    last_timestamp = -min_time_interval  # Initialize to allow first frame

    # Get time base for converting PTS to seconds
    time_base = video_stream.time_base if video_stream.time_base else None

    # Decode all frames
    for decoded_index, frame in enumerate(video_container.decode(video_stream)):
        # Get the presentation timestamp in seconds from the frame
        # Convert frame.pts from time base units to seconds
        if frame.pts is not None and time_base is not None:
            frame_pts_seconds = float(frame.pts * time_base)
        else:
            # Fallback to frame.time if pts or time_base is not available
            frame_pts_seconds = frame.time if frame.time is not None else -1.0

        # Apply FPS filtering if specified
        if fps is not None and fps > 0:
            # Only include frames that are at least min_time_interval apart
            if frame_pts_seconds - last_timestamp < min_time_interval:
                continue
            last_timestamp = frame_pts_seconds

        sample = VideoFrameCreate(
            frame_number=decoded_index,
            frame_timestamp_s=frame_pts_seconds,
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
