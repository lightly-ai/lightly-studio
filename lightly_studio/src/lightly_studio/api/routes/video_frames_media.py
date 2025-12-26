"""API routes for streaming video frames."""

from __future__ import annotations

import asyncio
import io
import os
import threading
from collections import OrderedDict
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import UUID

import cv2
import fsspec
import numpy as np
import numpy.typing as npt
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.db_manager import SessionDep
from lightly_studio.resolvers import video_frame_resolver

frames_router = APIRouter(prefix="/frames/media", tags=["frames streaming"])

# Thread pool for CPU-intensive video processing
_thread_pool_executor: ThreadPoolExecutor | None = None

# Thread-local cache for VideoCapture + stream (per thread, not shared)
_thread_local = threading.local()
_CAP_CACHE_SIZE = 4


def get_thread_pool_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor."""
    global _thread_pool_executor  # noqa: PLW0603
    if _thread_pool_executor is None:
        cpu_count = os.cpu_count() or 1
        # Use available cores - 1 but at least 1. Cap to prevent runaway usage.
        max_workers = max(1, min(cpu_count - 1 or 1, 16))
        _thread_pool_executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="video_frame"
        )
    return _thread_pool_executor


ROTATION_MAP: dict[int, Any] = {
    0: None,
    90: cv2.ROTATE_90_COUNTERCLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_CLOCKWISE,
}


class FSSpecStreamReader(io.BufferedIOBase):
    """Wrapper to make fsspec file objects compatible with cv2.VideoCapture's interface."""

    def __init__(self, path: str) -> None:
        """Initialize the stream reader.

        Args:
            path: Path to the video file (local path or cloud URL).
        """
        self.fs, self.fs_path = fsspec.core.url_to_fs(url=path)
        self.file = self.fs.open(path=self.fs_path, mode="rb")
        # Get file size for size() method
        try:
            self.file_size = self.file.size
        except AttributeError:
            # Fallback: seek to end to get size
            current_pos = self.file.tell()
            self.file.seek(0, 2)
            self.file_size = self.file.tell()
            self.file.seek(current_pos)

    def read(self, n: int | None = -1) -> bytes:
        """Read n bytes from the stream."""
        return cast(bytes, self.file.read(n))

    def read1(self, n: int = -1) -> bytes:
        """Read up to n bytes from the stream (implementation for BufferedIOBase)."""
        return cast(bytes, self.file.read(n))

    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to the given offset in the stream."""
        return cast(int, self.file.seek(offset, whence))

    def tell(self) -> int:
        """Return the current position in the stream."""
        return cast(int, self.file.tell())

    def size(self) -> int:
        """Return the total size of the stream."""
        return cast(int, self.file_size)

    def close(self) -> None:
        """Close the stream."""
        if not self.closed:
            self.file.close()
            super().close()

    def __enter__(self) -> FSSpecStreamReader:
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager and close the stream."""
        self.close()


def _get_cached_capture(video_path: str) -> cv2.VideoCapture:
    """Get a cached VideoCapture for a video file, or create new if not cached.

    This function implements a thread-local cache for VideoCapture objects and
    their underlying fsspec stream. Each thread in the thread pool maintains its
    own independent cache, allowing safe concurrent access without locking.

    Args:
        video_path: Path to the video file.

    Returns:
        Open cv2.VideoCapture object for the video.

    Raises:
        ValueError: If the video file cannot be opened.
    """
    if not hasattr(_thread_local, "cap_cache"):
        _thread_local.cap_cache = OrderedDict()
    cache: OrderedDict[str, tuple[cv2.VideoCapture, FSSpecStreamReader]] = _thread_local.cap_cache

    if video_path in cache:
        cap, stream = cache.pop(video_path)
        if cap.isOpened():
            cache[video_path] = (cap, stream)  # move to end
            return cap
        # stale entry
        stream.close()

    # open new
    stream = FSSpecStreamReader(video_path)
    cap = cv2.VideoCapture(cast(Any, stream), apiPreference=cv2.CAP_FFMPEG, params=())
    if not cap.isOpened():
        stream.close()
        raise ValueError(f"Could not open video: {video_path}")

    cache[video_path] = (cap, stream)
    # enforce cache size
    while len(cache) > _CAP_CACHE_SIZE:
        _, (old_cap, old_stream) = cache.popitem(last=False)
        old_cap.release()
        old_stream.close()

    return cap


def _process_video_frame(
    video_path: str,
    frame_number: int,
    rotation_deg: int,
    compressed: bool,
) -> tuple[npt.NDArray[np.uint8], str]:
    """Process a video frame (CPU-intensive work, runs in thread pool).

    This function extracts a single frame from a video file, applies any necessary
    transformations (rotation), and encodes it as PNG or JPEG. It uses a cached
    VideoCapture object to avoid reopening the video file for each frame request,
    which is especially beneficial for cloud-stored videos.

    Args:
        video_path: Path to the video file.
        frame_number: Frame number to extract.
        rotation_deg: Rotation in degrees.
        compressed: Whether to encode as JPEG with lower quality.

    Returns:
        Tuple of (encoded_buffer, media_type).

    Raises:
        ValueError: If frame cannot be processed.
    """
    cap = _get_cached_capture(video_path)

    # Seek to the correct frame and read it
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    # Do not release/close; cached for reuse

    if not ret:
        raise ValueError(f"No frame at index {frame_number}")

    # Apply counter-rotation if needed
    rotate_code = ROTATION_MAP[rotation_deg]
    if rotate_code is not None:
        frame = cv2.rotate(src=frame, rotateCode=rotate_code)

    # Encode frame - use JPEG with lower quality when compressed, PNG otherwise
    if compressed:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 60]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)
        media_type = "image/jpeg"
    else:
        success, buffer = cv2.imencode(".png", frame)
        media_type = "image/png"

    if not success:
        raise ValueError("Could not encode frame")

    return buffer, media_type


@frames_router.get("/{sample_id}")
async def stream_frame(
    sample_id: UUID, session: SessionDep, compressed: bool = False
) -> StreamingResponse:
    """Serve a single video frame as PNG/JPEG using StreamingResponse.

    Args:
        sample_id: The UUID of the video frame sample.
        session: Database session dependency.
        compressed: If True, encode as JPEG with lower quality (keeps original resolution).
    """
    video_frame = video_frame_resolver.get_by_id(session=session, sample_id=sample_id)
    video_path = video_frame.video.file_path_abs

    # Run CPU-intensive video processing in thread pool to avoid blocking event loop
    try:
        buffer, media_type = await asyncio.get_event_loop().run_in_executor(
            get_thread_pool_executor(),
            _process_video_frame,
            video_path,
            video_frame.frame_number,
            video_frame.rotation_deg,
            compressed,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    def frame_stream() -> Generator[bytes, None, None]:
        yield buffer.tobytes()

    return StreamingResponse(
        frame_stream(),
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Length": str(buffer.nbytes),
        },
    )
