from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import av
import numpy as np
from PIL import Image as PILImage
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoCreate, VideoFrameCreate, VideoTable
from lightly_studio.resolvers import (
    collection_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.type_definitions import PathLike


@dataclass
class VideoStub:
    """Helper class to represent a sample video for testing.

    Attributes:
        path: Location of the video file.
        width: Width of the video in pixels.
        height: Height of the video in pixels.
        duration: Duration of the video in seconds.
        fps: Frame rate of the video.

    """

    path: PathLike = "/path/to/video.mp4"
    width: int = 640
    height: int = 480
    duration_s: float = 12.3
    fps: float = 30.0


def create_video(session: Session, collection_id: UUID, video: VideoStub) -> VideoTable:
    sample_ids = video_resolver.create_many(
        session=session,
        collection_id=collection_id,
        samples=[
            VideoCreate(
                file_path_abs=str(video.path),
                file_name=Path(video.path).name,
                width=video.width,
                height=video.height,
                duration_s=video.duration_s,
                fps=video.fps,
            )
        ],
    )
    video_table = video_resolver.get_by_id(session=session, sample_id=sample_ids[0])
    assert video_table is not None
    return video_table


def create_videos(
    session: Session,
    collection_id: UUID,
    videos: list[VideoStub],
) -> list[UUID]:
    """Creates samples in the database for a given collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection to add samples to.
        videos: A list of SampleVideo objects representing the samples to create.

    Returns:
        A list of the created VideoTable objects IDs.
    """
    return video_resolver.create_many(
        session=session,
        collection_id=collection_id,
        samples=[
            VideoCreate(
                file_path_abs=str(video.path),
                file_name=Path(video.path).name,
                width=video.width,
                height=video.height,
                duration_s=video.duration_s,
                fps=video.fps,
            )
            for video in videos
        ],
    )


@dataclass
class VideoWithFrames:
    video_sample_id: UUID
    frame_sample_ids: list[UUID]
    video_frames_collection_id: UUID


def create_video_with_frames(
    session: Session,
    collection_id: UUID,
    video: VideoStub,
) -> VideoWithFrames:
    """Create a video sample with associated frame samples.

    Args:
        session: The database session.
        collection_id: The uuid of the collection to attach to.
        video: The video stub containing video metadata.

    Number of frames are calculated using the video's duration and fps.

    Returns:
        The video sample id and list of frame sample ids in a VideoWithFrames object.
    """
    video_sample_id = video_resolver.create_many(
        session=session,
        collection_id=collection_id,
        samples=[
            VideoCreate(
                file_path_abs=str(video.path),
                file_name=Path(video.path).name,
                width=video.width,
                height=video.height,
                duration_s=video.duration_s,
                fps=video.fps,
            )
        ],
    )[0]
    n_frames = int(video.duration_s * video.fps)

    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=session, collection_id=collection_id, sample_type=SampleType.VIDEO_FRAME
    )

    frame_samples = video_frame_resolver.create_many(
        session=session,
        collection_id=video_frames_collection_id,
        samples=[
            VideoFrameCreate(
                frame_number=i,
                frame_timestamp_s=i / video.fps,
                frame_timestamp_pts=i,
                parent_sample_id=video_sample_id,
            )
            for i in range(n_frames)
        ],
    )

    return VideoWithFrames(
        video_sample_id=video_sample_id,
        frame_sample_ids=frame_samples,
        video_frames_collection_id=video_frames_collection_id,
    )


def create_video_file(
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
