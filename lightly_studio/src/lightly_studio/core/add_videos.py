"""Functions to add samples and their annotations to a dataset in the database."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable
from uuid import UUID

import av
import fsspec
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.logging import (
    _LoadingLoggingContext,
    _log_loading_results,
)
from lightly_studio.models.video import VideoCreate, VideoFrameCreate
from lightly_studio.resolvers import (
    sample_resolver,
    video_frame_resolver,
    video_resolver,
)

SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


def load_video_into_dataset_from_paths(
    session: Session,
    dataset_id: UUID,
    video_paths: Iterable[str],
    fps: float | None = None,
) -> list[UUID]:
    """Load video frames from file paths into the dataset using PyAV.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load video frames into.
        video_paths: An iterable of file paths to the videos to load.
        fps: Optional FPS value to control frame extraction. If provided, only frames
            at the specified FPS intervals will be extracted. If None, all frames
            will be extracted.

    Returns:
        A list of UUIDs of the created samples.
    """
    video_samples_to_create: list[VideoCreate] = []

    created_sample_ids: list[UUID] = []

    # Count total frames across all videos for logging
    total_frames = 0
    for video_path in video_paths:
        try:
            fs, fs_path = fsspec.core.url_to_fs(video_path)
            content = fs.cat_file(fs_path)
            video_buffer = BytesIO(content)
            container = av.open(video_buffer)
            video_stream = container.streams.video[0]

            # Get video metadata
            num_frames = video_stream.frames
            if num_frames == 0:
                # If frames count is not available, estimate from duration
                duration = (
                    float(video_stream.duration * video_stream.time_base)
                    if video_stream.duration
                    else 0
                )
                framerate = float(video_stream.average_rate) if video_stream.average_rate else 30.0
                num_frames = int(duration * framerate)

            framerate = float(video_stream.average_rate) if video_stream.average_rate else 30.0

            # Get video dimensions
            video_width = video_stream.width if video_stream.width else 0
            video_height = video_stream.height if video_stream.height else 0

            video_duration = num_frames / framerate if framerate > 0 else 0
            if fps is not None and fps > 0:
                # Calculate how many frames we'll extract based on FPS
                frames_to_extract = int(video_duration * fps)
                total_frames += min(frames_to_extract, num_frames)
            else:
                total_frames += num_frames
            video_samples_to_create.append(
                VideoCreate(
                    file_path_abs=video_path,
                    width=video_width,
                    height=video_height,
                    duration=float(video_duration),
                    fps=fps,
                    file_name=Path(video_path).name,
                )
            )

            container.close()
        except Exception as e:
            print(f"Error reading video {video_path}: {e}")
            # If we can't decode the video, we'll skip it later
            continue
    video_sample_ids = video_resolver.create_many(
        session=session, samples=video_samples_to_create, dataset_id=dataset_id
    )
    if not video_sample_ids:
        return created_sample_ids
    logging_context = _LoadingLoggingContext(
        n_samples_to_be_inserted=total_frames,
        n_samples_before_loading=sample_resolver.count_by_dataset_id(
            session=session, dataset_id=dataset_id
        ),
    )

    for video_path in tqdm(
        video_paths,
        desc="Processing videos (PyAV)",
        unit=" videos",
    ):
        try:
            samples_to_create: list[VideoFrameCreate] = []
            # Open video with PyAV
            fs, fs_path = fsspec.core.url_to_fs(video_path)
            content = fs.cat_file(fs_path)
            video_buffer = BytesIO(content)
            container = av.open(video_buffer)
            video_stream = container.streams.video[0]

            # Get video metadata
            num_frames = video_stream.frames
            framerate = float(video_stream.average_rate) if video_stream.average_rate else 30.0
            time_base = video_stream.time_base

            # If frames count is not available, estimate from duration
            if num_frames == 0:
                duration = float(video_stream.duration * time_base) if video_stream.duration else 0
                num_frames = int(duration * framerate) if framerate > 0 else 0

            # Determine which frames to extract based on FPS parameter
            if fps is not None and fps > 0:
                # Calculate frame indices to extract based on desired FPS
                frame_interval = framerate / fps
                frame_indices = []
                current_frame = 0
                while current_frame < num_frames:
                    frame_indices.append(int(current_frame))
                    current_frame += frame_interval
            else:
                # Extract all frames
                frame_indices = list(range(num_frames))

            # Extract frames from the video
            if not frame_indices:
                # No frames to extract, skip this video
                container.close()
                continue

            sorted_frame_indices = sorted(frame_indices)
            frame_indices_set = set(frame_indices)
            current_frame_idx = 0
            max_frame_idx = max(sorted_frame_indices)

            try:
                for _frame in container.decode(video_stream):
                    # Check if this is a frame we need to extract
                    if current_frame_idx in frame_indices_set:
                        frame_idx = current_frame_idx

                        try:
                            # Calculate timestamp for this frame
                            frame_timestamp = frame_idx / framerate if framerate > 0 else 0.0

                            sample = VideoFrameCreate(
                                frame_number=frame_idx,
                                frame_timestamp=frame_timestamp,
                                video_sample_id=video_sample_ids[0],
                            )
                            samples_to_create.append(sample)

                            # Process batch when it reaches SAMPLE_BATCH_SIZE
                            if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
                                created_samples_batch = video_frame_resolver.create_many(
                                    session=session,
                                    samples=samples_to_create,
                                    dataset_id=dataset_id,
                                )
                                created_sample_ids.extend(created_samples_batch
                                )
                                samples_to_create = []

                        except Exception as e:
                            # Skip this frame if there's an error
                            print(
                                f"Error creating sample for frame {frame_idx} "
                                f"from {video_path}: {e}"
                            )
                            continue

                    current_frame_idx += 1

                    # Stop if we've extracted all needed frames
                    if current_frame_idx > max_frame_idx:
                        break

            finally:
                # Always close the container
                container.close()

        except Exception as e:
            print(f"Error processing video {video_path}: {e}")
            continue

    # Handle remaining samples
    if samples_to_create:
        created_samples_batch = video_frame_resolver.create_many(
            session=session,
            samples=samples_to_create,
            dataset_id=dataset_id,
        )
        created_sample_ids.extend(created_samples_batch)

    _log_loading_results(session=session, dataset_id=dataset_id, logging_context=logging_context)
    return created_sample_ids

