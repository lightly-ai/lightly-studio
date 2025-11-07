"""API routes for streaming frames."""

from __future__ import annotations

import fsspec
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.db_manager import SessionDep
import ffmpeg
import cv2
frames_router = APIRouter(prefix="/frames", tags=["frames streaming"])

@frames_router.get("/stream/{id}")
async def stream_frame(id: str, session: SessionDep):
    """Serve a single video frame as PNG using StreamingResponse."""
    video_frame = session.get(VideoFrameTable, id)
    if not video_frame:
        raise HTTPException(404, f"Video frame not found: {id}")

    cap = cv2.VideoCapture(video_frame.video.file_path_abs)
    if not cap.isOpened():
        return {"error": "Could not open video"}

    frame_number = int(video_frame.frame_number)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return {"error": f"No frame at timestamp {frame_number}"}

    success, buffer = cv2.imencode(".png", frame)
    if not success:
        return {"error": "Could not encode frame"}

    def frame_stream():
        yield buffer.tobytes()

    return StreamingResponse(frame_stream(), media_type="image/png")

