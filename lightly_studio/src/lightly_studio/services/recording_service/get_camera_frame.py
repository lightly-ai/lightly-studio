"""Reads a single displayable camera frame out of a recording's MCAP file."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from av import VideoFrame
from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.compressed_video import JPEG_QUALITY, VideoDecoder
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import DecodedMessage
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import (
    camera_jpeg_cache,
    reader_cache,
    video_decoder_cache,
)
from lightly_studio.services.recording_service.camera_jpeg_cache import JpegId

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

    A delta frame is decoded on top of its keyframe. Each GOP of the channel has one
    shared decoder that only moves forward, and each decoded picture is cached. A
    picture that the decoder passed and that is not in the cache is decoded again
    from the keyframe.

    Args:
        session: The database session.
        dataset_id: The dataset the recording is expected to belong to.
        recording_id: The recording to read the frame from.
        channel_id: The camera channel to read.
        keyframe_timestamp_ns: The exact log time of the keyframe, in nanoseconds,
            from the indexed locator's `keyframe_log_time_ns`.
        log_time_ns: The exact log time of the frame, in nanoseconds, from the indexed
            locator's `log_time_ns`. Defaults to `keyframe_timestamp_ns`.
        width: Output width in pixels. Aspect ratio is preserved when only one of
            `width` / `height` is given.
        height: Output height in pixels. Aspect ratio is preserved when only one of
            `width` / `height` is given.
        quality: JPEG quality (1-95).

    Returns:
        The frame, or `None` if the recording does not exist, does not belong to
        `dataset_id`, or the channel has no message at `keyframe_timestamp_ns` or at
        `log_time_ns`.

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

    start_ns = camera_read_start_ns(
        uri=recording.uri,
        channel_id=channel_id,
        keyframe_log_time_ns=keyframe_timestamp_ns,
        target_time_ns=target_time_ns,
        width=width,
        height=height,
        quality=quality,
    )
    messages: list[DecodedMessage] = []
    if start_ns is not None:
        with reader_cache.borrow_reader(uri=recording.uri) as reader:
            messages = reader.get_decoded_messages_in_range(
                channel_ids=[channel_id], start_time_ns=start_ns, end_time_ns=target_time_ns
            )[channel_id]
    data = camera_jpeg(
        uri=recording.uri,
        channel_id=channel_id,
        keyframe_log_time_ns=keyframe_timestamp_ns,
        messages=messages,
        target_time_ns=target_time_ns,
        width=width,
        height=height,
        quality=quality,
    )
    if data is None and start_ns != keyframe_timestamp_ns:
        with reader_cache.borrow_reader(uri=recording.uri) as reader:
            data = camera_jpeg_from_keyframe(
                reader=reader,
                uri=recording.uri,
                channel_id=channel_id,
                keyframe_log_time_ns=keyframe_timestamp_ns,
                target_time_ns=target_time_ns,
                width=width,
                height=height,
                quality=quality,
            )
    if data is None:
        return None
    return CameraFrame(data=data, media_type="image/jpeg", log_time_ns=target_time_ns)


def camera_jpeg(  # noqa: PLR0913
    uri: str,
    channel_id: int,
    keyframe_log_time_ns: int,
    messages: Sequence[DecodedMessage],
    target_time_ns: int,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes | None:
    """Returns the JPEG of a frame and caches each picture decoded on the way.

    Requests for one GOP run one after another on its decoder.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel to decode.
        keyframe_log_time_ns: The log time of the keyframe a new decoder starts at.
        messages: Messages of the channel in log time order. They must include the
            message at `target_time_ns`, and the keyframe when the decoder restarts.
        target_time_ns: The log time of the frame.
        width: Output width of the JPEG in pixels.
        height: Output height of the JPEG in pixels.
        quality: JPEG quality (1-95).

    Returns:
        The JPEG bytes, or `None` when `messages` has no message at `target_time_ns`,
        or a new decoder does not start with its keyframe.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`, or the target
            message exists but its picture cannot be decoded.
    """
    jpeg_id = JpegId(
        uri=uri,
        channel_id=channel_id,
        log_time_ns=target_time_ns,
        width=width,
        height=height,
        quality=quality,
    )
    cached = camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id)
    if cached is not None:
        return cached
    with video_decoder_cache.borrow_decoder(
        uri=uri, channel_id=channel_id, keyframe_log_time_ns=keyframe_log_time_ns
    ) as lease:
        # The request that held the decoder before can have cached this JPEG.
        cached = camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id)
        if cached is not None:
            return cached
        decoder = _continuing_decoder(
            lease=lease,
            keyframe_log_time_ns=keyframe_log_time_ns,
            target_time_ns=target_time_ns,
        )
        return _encode_through(decoder=decoder, messages=messages, jpeg_id=jpeg_id)


def camera_read_start_ns(  # noqa: PLR0913
    uri: str,
    channel_id: int,
    keyframe_log_time_ns: int,
    target_time_ns: int,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> int | None:
    """Returns the first log time to read for the `camera_jpeg` of a frame.

    The read starts after the last message the GOP's decoder was fed, or at the
    keyframe when the decoder cannot continue. The result is only a hint: another
    request can move the decoder before `camera_jpeg` borrows it. Then `camera_jpeg`
    returns `None` and the caller uses `camera_jpeg_from_keyframe`.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel.
        keyframe_log_time_ns: The log time of the keyframe of the frame.
        target_time_ns: The log time of the frame.
        width: Output width of the JPEG in pixels.
        height: Output height of the JPEG in pixels.
        quality: JPEG quality (1-95).

    Returns:
        The first log time to read, or `None` when the JPEG is cached.
    """
    jpeg_id = JpegId(
        uri=uri,
        channel_id=channel_id,
        log_time_ns=target_time_ns,
        width=width,
        height=height,
        quality=quality,
    )
    if camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id) is not None:
        return None
    decoder = video_decoder_cache.peek_decoder(
        uri=uri, channel_id=channel_id, keyframe_log_time_ns=keyframe_log_time_ns
    )
    if decoder is None or not decoder.can_continue_to(
        keyframe_log_time_ns=keyframe_log_time_ns, log_time_ns=target_time_ns
    ):
        return keyframe_log_time_ns
    if decoder.has_frame(log_time_ns=target_time_ns):
        return target_time_ns
    return _feed_start_ns(decoder=decoder)


def camera_jpeg_from_keyframe(  # noqa: PLR0913
    reader: McapFileReader,
    uri: str,
    channel_id: int,
    keyframe_log_time_ns: int,
    target_time_ns: int,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes | None:
    """Reads a camera channel from the keyframe and returns the JPEG of a frame.

    Use this when `camera_jpeg` returned `None` for messages that started after the
    keyframe.

    Args:
        reader: An open reader of the recording.
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel.
        keyframe_log_time_ns: The log time of the keyframe of the frame.
        target_time_ns: The log time of the frame.
        width: Output width of the JPEG in pixels.
        height: Output height of the JPEG in pixels.
        quality: JPEG quality (1-95).

    Returns:
        The JPEG bytes, or `None` when the channel has no message at `target_time_ns`.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`, or the target
            message exists but its picture cannot be decoded.
    """
    logger.debug(
        "Camera channel %s: reading again from the keyframe at %s.",
        channel_id,
        keyframe_log_time_ns,
    )
    messages = reader.get_decoded_messages_in_range(
        channel_ids=[channel_id], start_time_ns=keyframe_log_time_ns, end_time_ns=target_time_ns
    )[channel_id]
    return camera_jpeg(
        uri=uri,
        channel_id=channel_id,
        keyframe_log_time_ns=keyframe_log_time_ns,
        messages=messages,
        target_time_ns=target_time_ns,
        width=width,
        height=height,
        quality=quality,
    )


def _continuing_decoder(
    lease: video_decoder_cache.DecoderLease,
    keyframe_log_time_ns: int,
    target_time_ns: int,
) -> VideoDecoder:
    """Returns the leased decoder when it can reach the target, else a new one."""
    decoder = lease.decoder
    if decoder is not None and decoder.can_continue_to(
        keyframe_log_time_ns=keyframe_log_time_ns, log_time_ns=target_time_ns
    ):
        return decoder
    return lease.reset()


def _encode_through(
    decoder: VideoDecoder,
    messages: Sequence[DecodedMessage],
    jpeg_id: JpegId,
) -> bytes | None:
    """Feeds the decoder up to the target and caches the JPEG of each emitted picture.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`, or the target
            message exists but its picture cannot be decoded.
    """
    if decoder.has_frame(log_time_ns=jpeg_id.log_time_ns):
        return _store_held_frame(decoder=decoder, jpeg_id=jpeg_id)
    pending = _pending_messages(
        decoder=decoder, messages=messages, target_time_ns=jpeg_id.log_time_ns
    )
    if pending is None:
        return None
    _require_compressed_video(schema_name=pending[0].schema_name)
    for message in pending:
        _decode_and_store(decoder=decoder, message=message, jpeg_id=jpeg_id)
    data = camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id)
    if data is None:
        raise McapAccessError(
            f"No decodable frame at log time {jpeg_id.log_time_ns} on channel {jpeg_id.channel_id}."
        )
    return data


def _store_held_frame(decoder: VideoDecoder, jpeg_id: JpegId) -> bytes:
    """Caches the picture the decoder already holds, then releases it."""
    frame = decoder.frame(log_time_ns=jpeg_id.log_time_ns)
    assert frame is not None
    data = _store_jpeg(jpeg_id=jpeg_id, frame=frame)
    decoder.release_frames_up_to(log_time_ns=jpeg_id.log_time_ns)
    return data


def _decode_and_store(decoder: VideoDecoder, message: DecodedMessage, jpeg_id: JpegId) -> None:
    """Feeds one message and caches the picture it emits."""
    decoder.decode(decoded_message=message.decoded_message, log_time_ns=message.log_time_ns)
    frame = decoder.frame(log_time_ns=message.log_time_ns)
    if frame is None:
        return
    _store_jpeg(jpeg_id=replace(jpeg_id, log_time_ns=message.log_time_ns), frame=frame)
    decoder.release_frames_up_to(log_time_ns=message.log_time_ns)


def _pending_messages(
    decoder: VideoDecoder, messages: Sequence[DecodedMessage], target_time_ns: int
) -> list[DecodedMessage] | None:
    """Returns the messages the decoder still needs, or `None` when the target is absent.

    A new decoder must start with the message at its keyframe.
    """
    first_ns = _feed_start_ns(decoder=decoder)
    pending = [message for message in messages if first_ns <= message.log_time_ns <= target_time_ns]
    if not pending or pending[-1].log_time_ns != target_time_ns:
        return None
    if decoder.last_log_time_ns is None and pending[0].log_time_ns != decoder.keyframe_log_time_ns:
        return None
    return pending


def _store_jpeg(jpeg_id: JpegId, frame: VideoFrame) -> bytes:
    """Returns the cached JPEG of a picture, and encodes it when it is not cached."""
    cached = camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id)
    if cached is not None:
        return cached
    data = compressed_video.to_jpeg(
        frame=frame, width=jpeg_id.width, height=jpeg_id.height, quality=jpeg_id.quality
    )
    camera_jpeg_cache.put_jpeg(jpeg_id=jpeg_id, data=data)
    return data


def _feed_start_ns(decoder: VideoDecoder) -> int:
    """Returns the log time of the first message the decoder still needs.

    This is the keyframe for a new decoder, else the time after the last fed message.
    """
    if decoder.last_log_time_ns is None:
        return decoder.keyframe_log_time_ns
    return decoder.last_log_time_ns + 1


def _require_compressed_video(schema_name: str | None) -> None:
    """Raises if a camera schema is not `CompressedVideo`.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`.
    """
    schema = schema_name or ""
    message_type = schema.split("/")[-1].split(".")[-1]
    if message_type != "CompressedVideo":
        raise McapAccessError(f"Unsupported camera message schema: '{schema}'.")
