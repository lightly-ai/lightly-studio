"""API routes for streaming video frames."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Any
from uuid import UUID

import cv2
import ffmpeg  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.video import VideoFrameTable

frames_router = APIRouter(prefix="/frames/media", tags=["frames streaming"])


@lru_cache(maxsize=512)
def _get_video_metadata(video_path: str) -> dict[str, Any]:
    probe = ffmpeg.probe(video_path)
    return next(s for s in probe["streams"] if s["codec_type"] == "video")


@lru_cache(maxsize=512)
def _get_rotation(video_path: str) -> int:
    stream = _get_video_metadata(video_path)

    if "side_data_list" in stream:
        for sd in stream["side_data_list"]:
            if "rotation" in sd:
                return int(sd["rotation"])

    if "tags" in stream and "rotate" in stream["tags"]:
        return int(stream["tags"]["rotate"])

    return 0


ROTATION_MAP: dict[int, Any] = {
    90: cv2.ROTATE_90_COUNTERCLOCKWISE,
    -90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    -180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_CLOCKWISE,
    -270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


@frames_router.get("/{sample_id}")
async def stream_frame(sample_id: UUID, session: SessionDep) -> StreamingResponse:
    """Serve a single video frame as PNG using StreamingResponse."""
    video_frame = session.get(VideoFrameTable, sample_id)
    if not video_frame:
        raise HTTPException(404, f"Video frame not found: {sample_id}")

    video_path = video_frame.video.file_path_abs

    rotation = _get_rotation(video_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(400, f"Could not open video: {sample_id}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame.frame_number)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise HTTPException(400, f"No frame at index {video_frame.frame_number}")

    new_rotation = ROTATION_MAP.get(rotation)
    if new_rotation:
        frame = cv2.rotate(frame, new_rotation)

    success, buffer = cv2.imencode(".png", frame)
    if not success:
        raise HTTPException(400, f"Could not encode frame: {sample_id}")

    def frame_stream() -> Generator[bytes, None, None]:
        yield buffer.tobytes()

    return StreamingResponse(frame_stream(), media_type="image/png")
