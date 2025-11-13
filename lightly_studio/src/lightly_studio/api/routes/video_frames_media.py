"""API routes for streaming frames."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Dict, Union
from uuid import UUID

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.video import VideoFrameTable

frames_router = APIRouter(prefix="/frames/media", tags=["frames streaming"])


@frames_router.get("/{sample_id}")
async def stream_frame(sample_id: UUID, session: SessionDep) -> Union[StreamingResponse, Dict[str, Any]]:
    """Serve a single video frame as PNG using StreamingResponse."""
    video_frame = session.get(VideoFrameTable, sample_id)
    if not video_frame:
        raise HTTPException(404, f"Video frame not found: {id}")

    cap = cv2.VideoCapture(video_frame.video.file_path_abs)
    if not cap.isOpened():
        return {"error": "Could not open video"}

    cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame.frame_number)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return {"error": f"No frame at timestamp {video_frame.frame_number}"}

    success, buffer = cv2.imencode(".png", frame)
    if not success:
        return {"error": "Could not encode frame"}

    def frame_stream() -> Generator[bytes, None, None]:
        yield buffer.tobytes()

    return StreamingResponse(frame_stream(), media_type="image/png")
