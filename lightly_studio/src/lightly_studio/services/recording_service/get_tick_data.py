"""Reads and decodes the sensor data of one MCAP sequence tick with one read."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.compressed_video import VideoDecoder
from lightly_studio.core.mcap.reader import McapFileReader, range_cache
from lightly_studio.core.mcap.type_definitions import DecodedMessage, StaticTransform
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import (
    encode_point_cloud_message,
    get_camera_frame,
    load_static_transforms,
    reader_cache,
    resolve_tick,
    video_decoder_cache,
)

logger = logging.getLogger(__name__)


class TickPayloadKind(IntEnum):
    """The encoding of a tick payload."""

    POINT_CLOUD = 0
    """An Arrow IPC stream of the points."""
    CAMERA_JPEG = 1
    """A JPEG image of the camera frame."""


@dataclass(frozen=True)
class TickPayload:
    """The decoded data of one channel of a tick.

    Attributes:
        channel_id: The MCAP channel the data was read from.
        kind: The encoding of `data`.
        log_time_ns: The log time of the message, in nanoseconds.
        data: The encoded data.
    """

    channel_id: int
    kind: TickPayloadKind
    log_time_ns: int
    data: bytes


def get_tick_data(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    seq_number: int,
    target_frame_id: str | None = None,
    camera_height: int | None = None,
) -> list[TickPayload] | None:
    """Returns the point clouds and camera frames of one tick.

    All channels of the tick are read with one pass over the MCAP file. The window
    spans the smallest to the largest log time of the tick's channels. It starts
    earlier when a camera decoder must start at its keyframe. Each channel gives the
    message at its locator log time. A point cloud is encoded as an Arrow IPC stream,
    a camera frame as a JPEG.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        seq_number: The zero-based index of the tick.
        target_frame_id: The coordinate frame to express the points in, e.g. the
            world frame. A point cloud without transforms to it stays in its sensor
            frame. ``None`` keeps every point cloud in its sensor frame.
        camera_height: The height of the camera JPEGs in pixels. The aspect ratio is
            preserved. ``None`` keeps the recorded size.

    Returns:
        One payload per channel, point clouds first. A channel without a message at
        its locator log time is left out. ``None`` if the sequence does not exist,
        does not belong to `dataset_id`, or has no tick at `seq_number`.

    Raises:
        ChannelNotFoundError: If a channel of the tick is not in the recording's file.
        McapAccessError: If a message cannot be decoded.
    """
    tick = resolve_tick.resolve_tick(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id, seq_number=seq_number
    )
    if tick is None:
        return None
    recording = recording_resolver.get_by_id(session=session, recording_id=tick.recording_id)
    if recording is None:
        return None
    lidars = [mcap for mcap, kind in tick.channels.values() if kind is McapDataType.POINT_CLOUD]
    cameras = [
        mcap
        for mcap, kind in tick.channels.values()
        if kind is McapDataType.VIDEO_FRAME and mcap.keyframe_log_time_ns is not None
    ]
    if not lidars and not cameras:
        return []

    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        decoders = {
            camera.channel_id: _take_decoder(uri=recording.uri, camera=camera) for camera in cameras
        }
        start_ns = min(
            [mcap.log_time_ns for mcap in [*lidars, *cameras]]
            + [get_camera_frame.feed_start_ns(decoder=decoder) for decoder in decoders.values()]
        )
        end_ns = max(mcap.log_time_ns for mcap in [*lidars, *cameras])
        range_cache.reset_read_account()
        read_started = time.perf_counter()
        messages = reader.get_decoded_messages_in_range(
            channel_ids=[mcap.channel_id for mcap in [*lidars, *cameras]],
            start_time_ns=start_ns,
            end_time_ns=end_ns,
        )
        read_seconds = time.perf_counter() - read_started
        decode_started = time.perf_counter()
        payloads = _point_cloud_payloads(
            session=session,
            reader=reader,
            recording_id=tick.recording_id,
            lidars=lidars,
            messages=messages,
            target_frame_id=target_frame_id,
        ) + _camera_payloads(
            uri=recording.uri,
            cameras=cameras,
            decoders=decoders,
            messages=messages,
            camera_height=camera_height,
        )
        logger.info(
            "Tick %s: %s payloads, read %.0f ms (%s), decode %.0f ms.",
            seq_number,
            len(payloads),
            read_seconds * 1000,
            range_cache.describe_reads(),
            (time.perf_counter() - decode_started) * 1000,
        )
        return payloads


def _take_decoder(uri: str, camera: McapTable) -> VideoDecoder:
    """Returns the cached decoder of a camera if it can reach the tick's frame, else a new one."""
    assert camera.keyframe_log_time_ns is not None
    decoder = video_decoder_cache.take_decoder(uri=uri, channel_id=camera.channel_id)
    if decoder is not None and decoder.can_continue_to(
        keyframe_log_time_ns=camera.keyframe_log_time_ns, log_time_ns=camera.log_time_ns
    ):
        return decoder
    return VideoDecoder(keyframe_log_time_ns=camera.keyframe_log_time_ns)


def _point_cloud_payloads(  # noqa: PLR0913
    session: Session,
    reader: McapFileReader,
    recording_id: UUID,
    lidars: Sequence[McapTable],
    messages: Mapping[int, Sequence[DecodedMessage]],
    target_frame_id: str | None,
) -> list[TickPayload]:
    """Encodes the message of each lidar at its locator log time."""
    static_transforms: list[StaticTransform] = []
    if target_frame_id is not None and lidars:
        static_transforms = load_static_transforms.load_static_transforms(
            session=session, recording_id=recording_id
        )
    payloads = []
    for lidar in lidars:
        message = _message_at(messages=messages[lidar.channel_id], log_time_ns=lidar.log_time_ns)
        if message is None:
            logger.warning(
                "Point cloud channel %s has no message at %s.", lidar.channel_id, lidar.log_time_ns
            )
            continue
        payloads.append(
            TickPayload(
                channel_id=lidar.channel_id,
                kind=TickPayloadKind.POINT_CLOUD,
                log_time_ns=lidar.log_time_ns,
                data=encode_point_cloud_message.encode_point_cloud_message(
                    session=session,
                    reader=reader,
                    recording_id=recording_id,
                    message=message,
                    target_frame_id=target_frame_id,
                    static_transforms=static_transforms,
                ),
            )
        )
    return payloads


def _camera_payloads(
    uri: str,
    cameras: Sequence[McapTable],
    decoders: Mapping[int, VideoDecoder],
    messages: Mapping[int, Sequence[DecodedMessage]],
    camera_height: int | None,
) -> list[TickPayload]:
    """Decodes the frame of each camera at its locator log time as JPEG."""
    payloads = []
    for camera in cameras:
        decoder = decoders[camera.channel_id]
        frame = get_camera_frame.decode_camera_frame(
            decoder=decoder,
            messages=messages[camera.channel_id],
            channel_id=camera.channel_id,
            target_time_ns=camera.log_time_ns,
        )
        if frame is None:
            logger.warning(
                "Camera channel %s has no frame at %s.", camera.channel_id, camera.log_time_ns
            )
        else:
            payloads.append(
                TickPayload(
                    channel_id=camera.channel_id,
                    kind=TickPayloadKind.CAMERA_JPEG,
                    log_time_ns=camera.log_time_ns,
                    data=compressed_video.to_jpeg(frame=frame, height=camera_height),
                )
            )
            decoder.release_frames_up_to(log_time_ns=camera.log_time_ns)
        get_camera_frame.store_decoder(uri=uri, channel_id=camera.channel_id, decoder=decoder)
    return payloads


def _message_at(messages: Sequence[DecodedMessage], log_time_ns: int) -> DecodedMessage | None:
    """Returns the message at an exact log time."""
    return next((message for message in messages if message.log_time_ns == log_time_ns), None)
