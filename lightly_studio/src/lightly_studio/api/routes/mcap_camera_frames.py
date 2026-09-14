"""Virtual image URLs for camera frames stored in MCAP recordings."""

from __future__ import annotations

from uuid import UUID

import fsspec
from fastapi import APIRouter, Query
from fastapi.responses import Response
from mcap.reader import make_reader

from lightly_studio.core.mcap import compressed_image
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.resolvers import recording_resolver

app_router = APIRouter(prefix="/mcap/camera-frames", tags=["mcap"])
CAMERA_MATCH_WINDOW_NS = 100_000_000


@app_router.get("/recordings/{recording_id}")
def get_camera_frame(
    session: SessionDep,
    recording_id: UUID,
    channel_id: int = Query(ge=0),
    timestamp_ns: int = Query(ge=0),
) -> Response:
    """Return the nearest CompressedImage message as a browser-readable image response."""
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise NotFoundError(f"Recording not found: {recording_id}")

    fs, path = fsspec.core.url_to_fs(recording.uri)
    with fs.open(path, "rb") as stream:
        reader = make_reader(stream)
        messages = [
            (schema, message)
            for schema, channel, message in reader.iter_messages()
            if channel.id == channel_id
        ]
    if not messages:
        raise NotFoundError(
            f"No camera frame found for channel {channel_id} at timestamp {timestamp_ns}."
        )
    exact = [item for item in messages if item[1].log_time == timestamp_ns]
    if len(exact) > 1:
        raise ValueError(f"Timestamp {timestamp_ns} is not unique on channel {channel_id}.")
    nearest_distance = min(abs(message.log_time - timestamp_ns) for _, message in messages)
    if nearest_distance > CAMERA_MATCH_WINDOW_NS:
        raise NotFoundError(
            f"No camera frame found for channel {channel_id} near timestamp {timestamp_ns}."
        )
    nearest = [
        item for item in messages if abs(item[1].log_time - timestamp_ns) == nearest_distance
    ]
    if len(nearest) > 1:
        raise ValueError(f"Timestamp {timestamp_ns} is not unique on channel {channel_id}.")

    schema, message = nearest[0]
    if schema is None or "CompressedImage" not in schema.name:
        raise ValueError(f"Channel {channel_id} is not a CompressedImage channel.")
    image, media_type = compressed_image.decode_compressed_image(message.data)
    return Response(
        content=image,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
