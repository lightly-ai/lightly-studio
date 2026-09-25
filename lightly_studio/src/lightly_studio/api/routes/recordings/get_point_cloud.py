"""Route to serve one point-cloud channel as an Arrow IPC stream."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_NOT_FOUND
from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.services.recording_service.get_point_cloud import (
    get_point_cloud as get_point_cloud_service,
)

get_point_cloud_router = APIRouter()


class PointCloudQuery(BaseModel):
    """Query parameters selecting one point-cloud message."""

    channel_id: int = Query(description="The point-cloud channel to read.")
    timestamp_ns: int = Query(
        ge=0,
        description="Exact MCAP log time in nanoseconds from the tick's channel locator.",
    )


@get_point_cloud_router.get("/point-cloud")
def get_point_cloud(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    recording_id: Annotated[UUID, Path(title="Recording ID")],
    point_cloud_query: Annotated[PointCloudQuery, Depends(PointCloudQuery)],
) -> Response:
    """Return one channel's point data as an Arrow IPC stream."""
    try:
        point_cloud = get_point_cloud_service(
            session=session,
            dataset_id=dataset_id,
            recording_id=recording_id,
            channel_id=point_cloud_query.channel_id,
            timestamp_ns=point_cloud_query.timestamp_ns,
        )
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=str(exc)) from exc
    except McapAccessError as exc:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=str(exc)) from exc
    if point_cloud is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=(
                f"No point cloud at timestamp {point_cloud_query.timestamp_ns} on channel "
                f"{point_cloud_query.channel_id} of recording {recording_id} in dataset "
                f"{dataset_id}."
            ),
        )
    return Response(
        content=point_cloud.data,
        media_type="application/vnd.apache.arrow.stream",
        headers={
            "Content-Disposition": "inline; filename=point-cloud.arrow",
            "Content-Type": "application/vnd.apache.arrow.stream",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Log-Time-Ns": str(point_cloud.log_time_ns),
        },
    )
