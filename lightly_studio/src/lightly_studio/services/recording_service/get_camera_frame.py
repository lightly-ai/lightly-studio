"""Reads a single displayable camera frame out of a recording's MCAP file."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import NamedTuple
from uuid import UUID

from av import VideoFrame
from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.compressed_video import JPEG_QUALITY, VideoDecoder
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader, range_cache
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import reader_cache, video_decoder_cache

logger = logging.getLogger(__name__)


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


class _FrameRead(NamedTuple):
    """A decoded picture and the time spent reading and decoding it."""

    frame: VideoFrame | None
    read_seconds: float
    video_seconds: float


def get_camera_frame(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    recording_id: UUID,
    channel_id: int,
    keyframe_timestamp_ns: int,
    log_time_ns: int | None = None,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> CameraFrame | None:
    """Returns the camera frame at an exact log time on a channel.

    Decodes the messages of the channel from `keyframe_timestamp_ns` up to
    `log_time_ns`, so that a delta frame is decoded on top of its keyframe. Each
    picture is emitted as its message is fed, and the decoder is kept, so the next
    later frame of the GOP continues from this one.

    Both timestamps are expected to come from the indexed locator, so they must
    match existing messages exactly. The decoder only moves forward. A frame
    behind it is decoded again from the keyframe.

    Args:
        session: The database session.
        dataset_id: The dataset the recording is expected to belong to.
        recording_id: The recording to read the frame from.
        channel_id: The camera channel to read, e.g. from a recording summary's
            `camera_channels`.
        keyframe_timestamp_ns: The exact log time of the keyframe to start decoding
            at, in nanoseconds. Comes from the indexed locator's
            `keyframe_log_time_ns`.
        log_time_ns: The exact log time of the frame to return, in nanoseconds. Comes
            from the indexed locator's `log_time_ns`. Defaults to
            `keyframe_timestamp_ns`, which returns the keyframe.
        width: Output width in pixels. Aspect ratio is preserved when only one of
            `width` / `height` is given.
        height: Output height in pixels. Aspect ratio is preserved when only one of
            `width` / `height` is given.
        quality: JPEG quality (1-95).

    Returns:
        The matching frame, or `None` if the recording does not exist, does not
        belong to `dataset_id`, or the channel has no message at
        `keyframe_timestamp_ns` or at `log_time_ns`.

    Raises:
        ValueError: If `log_time_ns` is before `keyframe_timestamp_ns`.
        ChannelNotFoundError: If `channel_id` is not in the recording's file.
        McapAccessError: If the channel's messages cannot be decoded, or the schema
            is not `CompressedVideo`.
    """
    target_time_ns = keyframe_timestamp_ns if log_time_ns is None else log_time_ns
    if target_time_ns < keyframe_timestamp_ns:
        raise ValueError(
            f"The frame log time {target_time_ns} is before the keyframe log time "
            f"{keyframe_timestamp_ns}."
        )
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None or recording.dataset_id != dataset_id:
        return None

    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        decoder = video_decoder_cache.take_decoder(uri=recording.uri, channel_id=channel_id)
        if decoder is None or not decoder.can_continue_to(
            keyframe_log_time_ns=keyframe_timestamp_ns, log_time_ns=target_time_ns
        ):
            decoder = VideoDecoder(keyframe_log_time_ns=keyframe_timestamp_ns)
        range_cache.reset_read_account()
        frame_read = _frame_at(
            reader=reader, decoder=decoder, channel_id=channel_id, target_time_ns=target_time_ns
        )
        if frame_read.frame is None:
            _store_decoder(uri=recording.uri, channel_id=channel_id, decoder=decoder)
            _log_camera_frame(channel_id=channel_id, frame_read=frame_read, jpeg_seconds=0.0)
            return None

        jpeg_started = time.perf_counter()
        data = compressed_video.to_jpeg(
            frame=frame_read.frame, width=width, height=height, quality=quality
        )
        jpeg_seconds = time.perf_counter() - jpeg_started
        decoder.release_frames_up_to(log_time_ns=target_time_ns)
        _store_decoder(uri=recording.uri, channel_id=channel_id, decoder=decoder)
        _log_camera_frame(channel_id=channel_id, frame_read=frame_read, jpeg_seconds=jpeg_seconds)
        return CameraFrame(data=data, media_type="image/jpeg", log_time_ns=target_time_ns)


def _store_decoder(uri: str, channel_id: int, decoder: VideoDecoder) -> None:
    """Puts a decoder back when a later request can use it."""
    if decoder.is_reusable():
        video_decoder_cache.put_decoder(uri=uri, channel_id=channel_id, decoder=decoder)


def _log_camera_frame(channel_id: int, frame_read: _FrameRead, jpeg_seconds: float) -> None:
    """Logs how a camera frame split its time between reading, decoding, and JPEG."""
    logger.info(
        "Camera channel %s: read %.0f ms (%s), video %.0f ms, jpeg %.0f ms.",
        channel_id,
        frame_read.read_seconds * 1000,
        range_cache.describe_reads(),
        frame_read.video_seconds * 1000,
        jpeg_seconds * 1000,
    )


def _frame_at(
    reader: McapFileReader,
    decoder: VideoDecoder,
    channel_id: int,
    target_time_ns: int,
) -> _FrameRead:
    """Feeds the decoder until the target picture is available.

    Returns no frame when the channel has no message at the target log time. A new
    decoder must start with the message at its keyframe. `read_seconds` is the time
    spent reading messages. `video_seconds` is the time spent decoding pictures.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`, or the target
            message exists but its picture cannot be decoded.
    """
    if decoder.has_frame(target_time_ns):
        return _FrameRead(
            frame=decoder.frame(log_time_ns=target_time_ns), read_seconds=0.0, video_seconds=0.0
        )

    start_time_ns = (
        decoder.keyframe_log_time_ns
        if decoder.last_log_time_ns is None
        else decoder.last_log_time_ns + 1
    )
    read_started = time.perf_counter()
    messages = reader.get_decoded_messages_in_range(
        channel_id=channel_id, start_time_ns=start_time_ns, end_time_ns=target_time_ns
    )
    read_seconds = time.perf_counter() - read_started
    if not messages or messages[-1].log_time_ns != target_time_ns:
        return _FrameRead(frame=None, read_seconds=read_seconds, video_seconds=0.0)
    if decoder.last_log_time_ns is None and messages[0].log_time_ns != decoder.keyframe_log_time_ns:
        return _FrameRead(frame=None, read_seconds=read_seconds, video_seconds=0.0)

    _require_compressed_video(schema_name=messages[0].schema_name)
    video_started = time.perf_counter()
    for message in messages:
        if decoder.has_frame(target_time_ns):
            break
        decoder.decode(
            decoded_message=message.decoded_message,
            log_time_ns=message.log_time_ns,
            retain_log_time_ns=target_time_ns,
        )
    frame = decoder.frame(log_time_ns=target_time_ns)
    video_seconds = time.perf_counter() - video_started
    if frame is None:
        raise McapAccessError(
            f"No decodable frame at log time {target_time_ns} on channel {channel_id}."
        )
    return _FrameRead(frame=frame, read_seconds=read_seconds, video_seconds=video_seconds)


def _require_compressed_video(schema_name: str | None) -> None:
    """Raises if a camera schema is not `CompressedVideo`.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`.
    """
    schema = schema_name or ""
    message_type = schema.split("/")[-1].split(".")[-1]
    if message_type != "CompressedVideo":
        raise McapAccessError(f"Unsupported camera message schema: '{schema}'.")
