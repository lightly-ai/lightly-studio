"""Ready-to-render binary MCAP point-cloud frames."""

from __future__ import annotations

from uuid import UUID

import fsspec
from fastapi import APIRouter, Query
from fastapi.responses import Response
from mcap.reader import make_reader

from lightly_studio.core.mcap import point_cloud_binary
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.resolvers import recording_resolver

app_router = APIRouter(prefix="/mcap/frames", tags=["mcap"])
_MEDIA_TYPE = "application/vnd.lightly.point-cloud"


@app_router.get("/recordings/{recording_id}")
def get_binary_point_cloud_frame(
    session: SessionDep,
    recording_id: UUID,
    channel_id: int = Query(ge=0),
    timestamp_ns: int = Query(ge=0),
    point_budget: int = Query(default=350_000, ge=1, le=2_000_000),
) -> Response:
    """Return one indexed PointCloud2 frame as an LSPC binary buffer."""
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise NotFoundError(f"Recording not found: {recording_id}")

    fs, path = fsspec.core.url_to_fs(recording.uri)
    with fs.open(path, "rb") as stream:
        reader = make_reader(stream)
        matches = [
            message
            for _schema, channel, message in reader.iter_messages()
            if channel.id == channel_id and message.log_time == timestamp_ns
        ]
    if not matches:
        raise NotFoundError(
            f"No frame found for channel {channel_id} at timestamp {timestamp_ns}."
        )
    if len(matches) > 1:
        raise ValueError(
            f"Timestamp {timestamp_ns} is not unique on channel {channel_id}."
        )

    cloud = point_cloud_binary.encode_point_cloud_message(
        matches[0].data, timestamp_ns=timestamp_ns, point_budget=point_budget
    )
    headers = {"Cache-Control": "public, max-age=3600"}
    point_cloud_binary.add_binary_header_metadata(headers, cloud)
    return Response(content=cloud.payload, media_type=_MEDIA_TYPE, headers=headers)
