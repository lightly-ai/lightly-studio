"""API routes for streaming video frames."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from uuid import UUID

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.db_manager import SessionDep
from lightly_studio.resolvers import video_frame_resolver

frames_router = APIRouter(prefix="/frames/media", tags=["frames streaming"])


ROTATION_MAP: dict[int, Any] = {
    0: None,
    90: cv2.ROTATE_90_COUNTERCLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_CLOCKWISE,
}


@frames_router.get("/{sample_id}")
async def stream_frame(sample_id: UUID, session: SessionDep) -> StreamingResponse:
    """Serve a single video frame as PNG using StreamingResponse."""
    video_frame = video_frame_resolver.get_by_id(session=session, sample_id=sample_id)
    video_path = video_frame.video.file_path_abs

    # Open video with OpenCV
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(400, f"Could not open video: {video_path}")

    # Seek to the correct frame and read it
    cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame.frame_number)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise HTTPException(400, f"No frame at index {video_frame.frame_number}")

    # Apply counter-rotation if needed
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
