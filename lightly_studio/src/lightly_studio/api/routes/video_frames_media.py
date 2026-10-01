"""API routes for streaming video frames."""

from __future__ import annotations

import asyncio
import io
import threading
from collections import OrderedDict
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Annotated, cast
from uuid import UUID

import av
import fsspec
from av.container import InputContainer
from av.video.frame import VideoFrame
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel

from lightly_studio.database import db_manager
from lightly_studio.models.settings import GridViewThumbnailQualityType
from lightly_studio.resolvers import video_frame_resolver
from lightly_studio.utils import executor

frames_router = APIRouter(prefix="/frames/media", tags=["frames streaming"])

JPEG_QUALITY = 75

# Containers are thread-local because seeking and decoding mutate their state.
_thread_local = threading.local()
_CONTAINER_CACHE_SIZE = 4


@dataclass(frozen=True)
class FrameTransformOptions:
    """Controls transport-level frame resizing and encoding."""

    quality: GridViewThumbnailQualityType
    max_width: int | None
    max_height: int | None


class FrameTransformQuery(BaseModel):
    """Query parameters for frame transport quality."""

    quality: GridViewThumbnailQualityType = GridViewThumbnailQualityType.RAW
    max_width: int | None = Query(default=None, ge=1, le=4096)
    max_height: int | None = Query(default=None, ge=1, le=4096)


def _get_cached_container(video_path: str, reset: bool = False) -> InputContainer:
    """Reuse a thread-local container; own both the decoder and its underlying file."""
    if not hasattr(_thread_local, "container_cache"):
        _thread_local.container_cache = OrderedDict()
    cache: OrderedDict[str, tuple[InputContainer, ExitStack]] = _thread_local.container_cache
    if video_path in cache:
        container, resources = cache.pop(video_path)
        if not reset:
            cache[video_path] = (container, resources)
            return container
        resources.close()

    fs, fs_path = fsspec.core.url_to_fs(url=video_path)
    with ExitStack() as resources:
        if fsspec.utils.get_protocol(video_path) in {"s3", "gs", "gcs"}:
            # Previews need sparse reads, not large sequential prefetches.
            file = resources.enter_context(
                fs.open(
                    path=fs_path,
                    mode="rb",
                    block_size=256 * 2**10,
                    cache_type="blockcache",
                    cache_options={"maxblocks": 4},
                )
            )
        else:
            file = resources.enter_context(fs.open(path=fs_path, mode="rb"))
        container = cast(InputContainer, resources.enter_context(av.open(file=file, mode="r")))
        if not container.streams.video:
            raise ValueError(f"No video stream in {video_path}")
        cache[video_path] = (container, resources.pop_all())
    while len(cache) > _CONTAINER_CACHE_SIZE:
        _, (_, old_resources) = cache.popitem(last=False)
        old_resources.close()
    return container


def _decode_video_frame(
    video_path: str,
    frame_number: int,
    frame_timestamp_pts: int,
) -> VideoFrame:
    """Seek by stored PTS, falling back to the original ordinal if no match exists."""
    if frame_timestamp_pts != -1:
        container = _get_cached_container(video_path=video_path)
        stream = container.streams.video[0]
        try:
            container.seek(frame_timestamp_pts, stream=stream, backward=True, any_frame=False)
            for frame in container.decode(stream):
                if frame.pts == frame_timestamp_pts:
                    return frame
                if frame.pts is not None and frame.pts > frame_timestamp_pts:
                    break
        except av.FFmpegError:
            # Some containers cannot seek; reopening also resets decoder state.
            pass

    container = _get_cached_container(video_path=video_path, reset=True)
    for index, frame in enumerate(container.decode(video=0)):
        if index == frame_number:
            return frame
    raise ValueError(f"No frame at index {frame_number}")


def _process_video_frame(
    video_path: str,
    frame_number: int,
    frame_timestamp_pts: int,
    rotation_deg: int,
    transform: FrameTransformOptions,
) -> tuple[bytes, str]:
    """Decode, counter-rotate, resize and encode a frame in the media worker pool."""
    frame = _decode_video_frame(
        video_path=video_path,
        frame_number=frame_number,
        frame_timestamp_pts=frame_timestamp_pts,
    )
    image = Image.fromarray(frame.to_ndarray(format="rgb24"))
    if rotation_deg:
        image = image.rotate(angle=rotation_deg, expand=True)
    buffer = io.BytesIO()
    if transform.quality == GridViewThumbnailQualityType.HIGH:
        image = _resize_frame(
            image=image,
            max_width=transform.max_width,
            max_height=transform.max_height,
        )
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, subsampling=2)
        media_type = "image/jpeg"
    else:
        image.save(buffer, format="PNG")
        media_type = "image/png"
    return buffer.getvalue(), media_type


def _resize_frame(
    image: Image.Image,
    max_width: int | None,
    max_height: int | None,
) -> Image.Image:
    """Resize a frame while preserving aspect ratio and avoiding upscaling."""
    scale = min(
        (max_width or image.width) / image.width, (max_height or image.height) / image.height, 1
    )
    if scale == 1:
        return image
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size=size, resample=Image.Resampling.BOX)


@frames_router.get("/{sample_id}")
async def stream_frame(
    sample_id: UUID,
    transform_query: Annotated[FrameTransformQuery, Depends(FrameTransformQuery)],
) -> Response:
    """Serve a single video frame as PNG/JPEG.

    Args:
        sample_id: The UUID of the video frame sample.
        transform_query: Transport-level query parameters for frame encoding.
    """
    # Avoid SessionDep here: FastAPI runs its sync-generator dependency on
    # Starlette's threadpool, exhausting threadpool slots under load. Manage
    # the session inline and close it before frame extraction.
    with db_manager.session() as sess:
        video_frame = video_frame_resolver.get_by_id(session=sess, sample_id=sample_id)
        video_path = video_frame.video.file_path_abs
        frame_number = video_frame.frame_number
        frame_timestamp_pts = video_frame.frame_timestamp_pts
        rotation_deg = video_frame.rotation_deg
    if (
        transform_query.quality == GridViewThumbnailQualityType.HIGH
        and transform_query.max_width is None
        and transform_query.max_height is None
    ):
        raise HTTPException(400, "max_width or max_height is required when quality=high")
    transform = FrameTransformOptions(
        quality=transform_query.quality,
        max_width=transform_query.max_width,
        max_height=transform_query.max_height,
    )

    # Run CPU-intensive video processing in thread pool to avoid blocking event loop
    try:
        buffer, media_type = await asyncio.get_running_loop().run_in_executor(
            executor.get_media_executor("video_frame"),
            _process_video_frame,
            video_path,
            frame_number,
            frame_timestamp_pts,
            rotation_deg,
            transform,
        )
    except (ValueError, av.FFmpegError) as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(
        content=buffer,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Length": str(len(buffer)),
        },
    )
