"""Reads a single displayable camera frame out of a recording's MCAP file."""

from __future__ import annotations

import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from uuid import UUID

import fsspec.utils
from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.compressed_video import JPEG_QUALITY
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import DecodedMessage
from lightly_studio.resolvers import recording_resolver

# Readers are thread-local because iter_decoded_messages seeks the underlying stream.
_thread_local = threading.local()
_READER_CACHE_SIZE = 4
_REMOTE_PROTOCOLS = {"s3", "gs", "gcs"}


@dataclass(frozen=True)
class CameraFrame:
    """An encoded camera frame, ready to serve as an HTTP response body.

    Attributes:
        data: The encoded image bytes, e.g. a JPEG file.
        media_type: The HTTP media type of `data`, e.g. `image/jpeg`.
        log_time_ns: The log time of the frame actually returned.
    """

    data: bytes
    media_type: str
    log_time_ns: int


def _get_cached_reader(uri: str) -> McapFileReader:
    """Returns a thread-local cached reader for a recording URI.

    Keeps up to `_READER_CACHE_SIZE` readers open per thread, evicting the least recently
    used on overflow. Remote S3 URIs include the endpoint from the environment when set,
    so local S3 emulators (e.g. Floci/LocalStack) work without extra configuration.
    """
    if not hasattr(_thread_local, "reader_cache"):
        _thread_local.reader_cache = OrderedDict()
    cache: OrderedDict[str, McapFileReader] = _thread_local.reader_cache
    if uri in cache:
        cache.move_to_end(uri)
        return cache[uri]
    protocol = fsspec.utils.get_protocol(uri)
    storage_options: dict[str, object] | None = None
    if protocol in _REMOTE_PROTOCOLS:
        # Build S3-compatible options.  If AWS_ENDPOINT_URL is set in the environment
        # (e.g. for a local Floci/LocalStack emulator), pass it via client_kwargs so
        # s3fs receives it correctly.  Do NOT pass cache_type here — older s3fs versions
        # forward unknown kwargs to the boto3 client constructor, causing a TypeError.
        endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
        if endpoint_url:
            storage_options = {"client_kwargs": {"endpoint_url": endpoint_url}}
    reader = McapFileReader(uri, storage_options=storage_options)
    cache[uri] = reader
    while len(cache) > _READER_CACHE_SIZE:
        _, evicted = cache.popitem(last=False)
        evicted.close()
    return reader


def get_camera_frame(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    recording_id: UUID,
    channel_id: int,
    keyframe_timestamp_ns: int,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> CameraFrame | None:
    """Returns the camera frame at an exact keyframe timestamp on a channel.

    Fetches the message at `keyframe_timestamp_ns` directly without scanning the full
    channel index. The timestamp is expected to come from the indexed locator's
    `keyframe_log_time_ns`, so it must match an existing message exactly.

    Args:
        session: The database session.
        dataset_id: The dataset the recording is expected to belong to.
        recording_id: The recording to read the frame from.
        channel_id: The camera channel to read, e.g. from a recording summary's
            `camera_channels`.
        keyframe_timestamp_ns: The exact log time of the keyframe to fetch, in
            nanoseconds. Comes from the indexed locator's `keyframe_log_time_ns`.
        width: Output width in pixels. Aspect ratio is preserved when only one of
            `width` / `height` is given.
        height: Output height in pixels. Aspect ratio is preserved when only one of
            `width` / `height` is given.
        quality: JPEG quality (1-95).

    Returns:
        The matching frame, or `None` if the recording does not exist, does not
        belong to `dataset_id`, or the channel has no message at
        `keyframe_timestamp_ns`.

    Raises:
        ChannelNotFoundError: If `channel_id` is not in the recording's file.
        McapAccessError: If the channel's messages cannot be decoded, or the schema
            is not `CompressedVideo`.
    """
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None or recording.dataset_id != dataset_id:
        return None

    reader = _get_cached_reader(recording.uri)
    nearest = reader.get_decoded_message_at(
        channel_id=channel_id, timestamp_ns=keyframe_timestamp_ns
    )
    if nearest is None:
        return None
    return _camera_frame_from_decoded(nearest, width=width, height=height, quality=quality)


def _camera_frame_from_decoded(
    message: DecodedMessage,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> CameraFrame:
    """Converts a decoded MCAP message into a servable camera frame.

    Args:
        message: A decoded message from `McapFileReader.get_decoded_message_at`.
        width: Output width in pixels; preserves aspect ratio when `height` is unset.
        height: Output height in pixels; preserves aspect ratio when `width` is unset.
        quality: JPEG quality (1-95).

    Returns:
        The decoded frame as JPEG.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`, or the payload
            cannot be decoded.
    """
    schema = message.schema_name or ""
    message_type = schema.split("/")[-1].split(".")[-1]
    if message_type != "CompressedVideo":
        raise McapAccessError(f"Unsupported camera message schema: '{schema}'.")
    data = compressed_video.from_decoded_message(
        message.decoded_message, width=width, height=height, quality=quality
    )
    return CameraFrame(data=data, media_type="image/jpeg", log_time_ns=message.log_time_ns)
