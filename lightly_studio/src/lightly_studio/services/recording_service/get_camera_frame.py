"""Reads a single displayable camera frame out of a recording's MCAP file."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from av import VideoFrame
from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.compressed_video import JPEG_QUALITY, VideoDecoder
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import DecodedMessage
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import reader_cache, video_decoder_cache


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
    target_time_ns = _target_time_ns(
        keyframe_timestamp_ns=keyframe_timestamp_ns, log_time_ns=log_time_ns
    )
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None or recording.dataset_id != dataset_id:
        return None

    reader = reader_cache.get_cached_reader(uri=recording.uri)
    decoder = _take_decoder(
        uri=recording.uri,
        channel_id=channel_id,
        keyframe_log_time_ns=keyframe_timestamp_ns,
        target_time_ns=target_time_ns,
    )
    frame = _frame_at(
        reader=reader,
        decoder=decoder,
        channel_id=channel_id,
        keyframe_timestamp_ns=keyframe_timestamp_ns,
        target_time_ns=target_time_ns,
    )
    if frame is None:
        _store_decoder(uri=recording.uri, channel_id=channel_id, decoder=decoder)
        return None

    data = compressed_video.to_jpeg(frame=frame, width=width, height=height, quality=quality)
    decoder.release_frames_up_to(log_time_ns=target_time_ns)
    _store_decoder(uri=recording.uri, channel_id=channel_id, decoder=decoder)
    return CameraFrame(data=data, media_type="image/jpeg", log_time_ns=target_time_ns)


def _target_time_ns(keyframe_timestamp_ns: int, log_time_ns: int | None) -> int:
    """Returns the log time to decode, and rejects a frame that precedes its keyframe.

    Raises:
        ValueError: If `log_time_ns` is before `keyframe_timestamp_ns`.
    """
    target_time_ns = keyframe_timestamp_ns if log_time_ns is None else log_time_ns
    if target_time_ns < keyframe_timestamp_ns:
        raise ValueError(
            f"The frame log time {target_time_ns} is before the keyframe log time "
            f"{keyframe_timestamp_ns}."
        )
    return target_time_ns


def _take_decoder(
    uri: str, channel_id: int, keyframe_log_time_ns: int, target_time_ns: int
) -> VideoDecoder:
    """Returns the cached decoder of a channel if it can produce the target frame.

    Otherwise returns a new decoder that starts at the keyframe.
    """
    decoder = video_decoder_cache.take_decoder(uri=uri, channel_id=channel_id)
    if decoder is not None and decoder.can_continue_to(
        keyframe_log_time_ns=keyframe_log_time_ns, log_time_ns=target_time_ns
    ):
        return decoder
    return VideoDecoder(keyframe_log_time_ns=keyframe_log_time_ns)


def _store_decoder(uri: str, channel_id: int, decoder: VideoDecoder) -> None:
    """Puts a decoder back when a later request can use it."""
    if decoder.is_reusable():
        video_decoder_cache.put_decoder(uri=uri, channel_id=channel_id, decoder=decoder)


def _frame_at(
    reader: McapFileReader,
    decoder: VideoDecoder,
    channel_id: int,
    keyframe_timestamp_ns: int,
    target_time_ns: int,
) -> VideoFrame | None:
    """Feeds the decoder until the target picture is available.

    Returns `None` when the channel has no message at the target log time.

    Raises:
        McapAccessError: If the target message exists but its picture cannot be decoded.
    """
    if decoder.has_frame(target_time_ns):
        return decoder.frame(log_time_ns=target_time_ns)
    if not _feed_through_target(
        reader=reader,
        decoder=decoder,
        channel_id=channel_id,
        keyframe_timestamp_ns=keyframe_timestamp_ns,
        target_time_ns=target_time_ns,
    ):
        return None
    frame = decoder.frame(log_time_ns=target_time_ns)
    if frame is None:
        raise McapAccessError(
            f"No decodable frame at log time {target_time_ns} on channel {channel_id}."
        )
    return frame


def _feed_through_target(
    reader: McapFileReader,
    decoder: VideoDecoder,
    channel_id: int,
    keyframe_timestamp_ns: int,
    target_time_ns: int,
) -> bool:
    """Feeds messages from the decoder's position through the target message.

    Returns whether the channel has a message at `target_time_ns`. A new decoder
    must start with the message at its keyframe.
    """
    start_time_ns = (
        keyframe_timestamp_ns if decoder.last_log_time_ns is None else decoder.last_log_time_ns + 1
    )
    if start_time_ns > target_time_ns:
        return False
    messages = reader.get_decoded_messages_in_range(
        channel_id=channel_id, start_time_ns=start_time_ns, end_time_ns=target_time_ns
    )
    if not _reaches_target(decoder=decoder, messages=messages, target_time_ns=target_time_ns):
        return False
    _feed(decoder=decoder, messages=messages, retain_log_time_ns=target_time_ns)
    return True


def _feed(
    decoder: VideoDecoder, messages: Sequence[DecodedMessage], retain_log_time_ns: int
) -> None:
    """Feeds messages to the decoder, keeping pictures at or after `retain_log_time_ns`.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`.
    """
    if not messages:
        return
    _require_compressed_video(schema_name=messages[0].schema_name)
    for message in messages:
        if decoder.has_frame(retain_log_time_ns):
            break
        decoder.decode(
            decoded_message=message.decoded_message,
            log_time_ns=message.log_time_ns,
            retain_log_time_ns=retain_log_time_ns,
        )


def _reaches_target(
    decoder: VideoDecoder, messages: Sequence[DecodedMessage], target_time_ns: int
) -> bool:
    """Returns whether feeding `messages` to `decoder` ends at the target frame.

    A new decoder must start with the message at its keyframe.
    """
    if decoder.last_log_time_ns is None and (
        not messages or messages[0].log_time_ns != decoder.keyframe_log_time_ns
    ):
        return False
    last_log_time_ns = messages[-1].log_time_ns if messages else decoder.last_log_time_ns
    return last_log_time_ns == target_time_ns


def _require_compressed_video(schema_name: str | None) -> None:
    """Raises if a camera schema is not `CompressedVideo`.

    Raises:
        McapAccessError: If the schema is not `CompressedVideo`.
    """
    schema = schema_name or ""
    message_type = schema.split("/")[-1].split(".")[-1]
    if message_type != "CompressedVideo":
        raise McapAccessError(f"Unsupported camera message schema: '{schema}'.")
