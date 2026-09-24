"""API routes for recordings.

Each route handler is defined in its own module with its own ``APIRouter``. This
barrel aggregates them into a single ``recordings_router`` mounted by the
application.
"""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.routes.recordings.get_camera_frame import get_camera_frame_router
from lightly_studio.api.routes.recordings.get_point_cloud import get_point_cloud_router

recordings_router = APIRouter(
    prefix="/datasets/{dataset_id}/recordings/{recording_id}", tags=["recordings"]
)
recordings_router.include_router(get_camera_frame_router)
recordings_router.include_router(get_point_cloud_router)

__all__ = ["recordings_router"]
