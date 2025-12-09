"""API routes for streaming video frames."""

from __future__ import annotations

import io
import logging
from collections.abc import Generator
from typing import Any, cast
from uuid import UUID

import cv2
import fsspec
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.db_manager import SessionDep
from lightly_studio.resolvers import video_frame_resolver

logger = logging.getLogger(__name__)

frames_router = APIRouter(prefix="/frames/media", tags=["frames streaming"])


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


@frames_router.get("/{sample_id}")
async def stream_frame(sample_id: UUID, session: SessionDep) -> StreamingResponse:
    """Serve a single video frame as PNG using StreamingResponse."""
    video_frame = video_frame_resolver.get_by_id(session=session, sample_id=sample_id)
    video_path = video_frame.video.file_path_abs

    # Open video with cv2.VideoCapture using fsspec stream.
    stream = FSSpecStreamReader(video_path)
    try:
        cap = cv2.VideoCapture(cast(Any, stream), apiPreference=cv2.CAP_FFMPEG, params=())
        if not cap.isOpened():
            raise HTTPException(400, f"Could not open video: {video_path}")
        # Seek to the correct frame and read it
        cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame.frame_number)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise HTTPException(400, f"No frame at index {video_frame.frame_number}")

        # Apply counter-rotation if needed.
        rotate_code = ROTATION_MAP[video_frame.rotation_deg]
        if rotate_code is not None:
            frame = cv2.rotate(src=frame, rotateCode=rotate_code)

        # Encode frame as PNG
        success, buffer = cv2.imencode(".png", frame)
        if not success:
            raise HTTPException(400, f"Could not encode frame: {sample_id}")

        def frame_stream() -> Generator[bytes, None, None]:
            yield buffer.tobytes()

        return StreamingResponse(frame_stream(), media_type="image/png")
    finally:
        stream.close()
