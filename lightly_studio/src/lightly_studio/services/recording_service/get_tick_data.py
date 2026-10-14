"""Reads and decodes the sensor data of one MCAP sequence tick with one read."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import IntEnum
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.reader import McapFileReader, read_account
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
)

logger = logging.getLogger(__name__)

# One worker per camera, capped so a tick with many cameras does not start one thread each.
_MAX_CAMERA_WORKERS = 8
# The recording time after a tick whose chunks are downloaded in the background, so
# that the next ticks of a playback find them in memory.
_READ_AHEAD_NS = 2_000_000_000


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
    starts at the earliest camera keyframe, so a decoder can restart, and ends at the
    latest log time of the tick. The cameras of the tick are decoded together. Each
    camera keeps one decoder, and every picture decoded on the way is cached, so
    another tick that asks for it does not decode it again. A point cloud is encoded
    as an Arrow IPC stream, a camera frame as a JPEG.

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

    channel_ids = [mcap.channel_id for mcap in [*lidars, *cameras]]
    end_time_ns = max(mcap.log_time_ns for mcap in [*lidars, *cameras])
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        read_account.reset()
        read_started = time.perf_counter()
        messages = reader.get_decoded_messages_in_range(
            channel_ids=channel_ids,
            start_time_ns=_window_start_ns(lidars=lidars, cameras=cameras),
            end_time_ns=end_time_ns,
        )
        read_seconds = time.perf_counter() - read_started
        reader.read_ahead(
            channel_ids=channel_ids,
            start_time_ns=end_time_ns + 1,
            end_time_ns=end_time_ns + _READ_AHEAD_NS,
        )
        decode_started = time.perf_counter()
        payloads = _decode_payloads(
            session=session,
            reader=reader,
            recording_id=tick.recording_id,
            uri=recording.uri,
            lidars=lidars,
            cameras=cameras,
            messages=messages,
            target_frame_id=target_frame_id,
            camera_height=camera_height,
        )
        logger.info(
            "Tick %s: %s payloads, read %.0f ms (%s), decode %.0f ms.",
            seq_number,
            len(payloads),
            read_seconds * 1000,
            read_account.describe(),
            (time.perf_counter() - decode_started) * 1000,
        )
        return payloads


def _window_start_ns(lidars: Sequence[McapTable], cameras: Sequence[McapTable]) -> int:
    """Returns the first log time the tick must read, including camera keyframes."""
    times = [lidar.log_time_ns for lidar in lidars]
    for camera in cameras:
        assert camera.keyframe_log_time_ns is not None
        times.append(camera.keyframe_log_time_ns)
    return min(times)


def _decode_payloads(  # noqa: PLR0913
    session: Session,
    reader: McapFileReader,
    recording_id: UUID,
    uri: str,
    lidars: Sequence[McapTable],
    cameras: Sequence[McapTable],
    messages: Mapping[int, Sequence[DecodedMessage]],
    target_frame_id: str | None,
    camera_height: int | None,
) -> list[TickPayload]:
    """Encodes the point clouds and, at the same time, the camera JPEGs of the tick."""
    if not cameras:
        return _point_cloud_payloads(
            session=session,
            reader=reader,
            recording_id=recording_id,
            lidars=lidars,
            messages=messages,
            target_frame_id=target_frame_id,
        )
    worker_count = min(_MAX_CAMERA_WORKERS, len(cameras))

    def encode(camera: McapTable) -> TickPayload | None:
        return _camera_payload(
            uri=uri, camera=camera, messages=messages, camera_height=camera_height
        )

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(encode, camera) for camera in cameras]
        # Point clouds use the database session, so they stay on this thread while the
        # cameras decode.
        point_clouds = _point_cloud_payloads(
            session=session,
            reader=reader,
            recording_id=recording_id,
            lidars=lidars,
            messages=messages,
            target_frame_id=target_frame_id,
        )
        return point_clouds + _camera_results(futures=futures)


def _camera_results(futures: Sequence[Future[TickPayload | None]]) -> list[TickPayload]:
    """Returns the camera payloads in request order, leaving out channels with no frame."""
    payloads = []
    for future in futures:
        payload = future.result()
        if payload is not None:
            payloads.append(payload)
    return payloads


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


def _camera_payload(
    uri: str,
    camera: McapTable,
    messages: Mapping[int, Sequence[DecodedMessage]],
    camera_height: int | None,
) -> TickPayload | None:
    """Decodes the frame of one camera at its locator log time as JPEG."""
    assert camera.keyframe_log_time_ns is not None
    data = get_camera_frame.camera_jpeg(
        uri=uri,
        channel_id=camera.channel_id,
        keyframe_log_time_ns=camera.keyframe_log_time_ns,
        messages=messages[camera.channel_id],
        target_time_ns=camera.log_time_ns,
        height=camera_height,
    )
    if data is None:
        logger.warning(
            "Camera channel %s has no frame at %s.", camera.channel_id, camera.log_time_ns
        )
        return None
    return TickPayload(
        channel_id=camera.channel_id,
        kind=TickPayloadKind.CAMERA_JPEG,
        log_time_ns=camera.log_time_ns,
        data=data,
    )


def _message_at(messages: Sequence[DecodedMessage], log_time_ns: int) -> DecodedMessage | None:
    """Returns the message at an exact log time."""
    return next((message for message in messages if message.log_time_ns == log_time_ns), None)
