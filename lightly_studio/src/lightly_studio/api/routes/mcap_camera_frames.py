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


@app_router.get("/recordings/{recording_id}")
def get_camera_frame(
    session: SessionDep,
    recording_id: UUID,
    channel_id: int = Query(ge=0),
    timestamp_ns: int = Query(ge=0),
) -> Response:
    """Return one CompressedImage message as a browser-readable image response."""
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise NotFoundError(f"Recording not found: {recording_id}")

    fs, path = fsspec.core.url_to_fs(recording.uri)
    with fs.open(path, "rb") as stream:
        reader = make_reader(stream)
        matches = [
            (schema, message)
            for schema, channel, message in reader.iter_messages()
            if channel.id == channel_id and message.log_time == timestamp_ns
        ]
    if not matches:
        raise NotFoundError(
            f"No camera frame found for channel {channel_id} at timestamp {timestamp_ns}."
        )
    if len(matches) > 1:
        raise ValueError(f"Timestamp {timestamp_ns} is not unique on channel {channel_id}.")

    schema, message = matches[0]
    if schema is None or "CompressedImage" not in schema.name:
        raise ValueError(f"Channel {channel_id} is not a CompressedImage channel.")
    image, media_type = compressed_image.decode_compressed_image(message.data)
    return Response(
        content=image,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
