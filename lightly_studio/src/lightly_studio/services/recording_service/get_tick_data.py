"""Reads and decodes the sensor data of one MCAP sequence tick with one read."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import IntEnum
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.reader import McapFileReader
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

    All channels of the tick are read with one pass over the MCAP file. A lidar
    decodes only its message at the locator log time. A camera continues the decoder
    of its GOP, see `get_camera_frame.camera_jpeg`. A point cloud is encoded as an
    Arrow IPC stream, a camera frame as a JPEG.

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

    camera_starts_ns = {
        camera.channel_id: get_camera_frame.camera_read_start_ns(
            uri=recording.uri,
            channel_id=camera.channel_id,
            keyframe_log_time_ns=_keyframe_ns(camera=camera),
            target_time_ns=camera.log_time_ns,
            height=camera_height,
        )
        for camera in cameras
    }
    # Keep the reader until the payloads are encoded. A point cloud can read dynamic
    # transforms from the file, and a camera whose decoder moved on reads again.
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        messages = reader.get_decoded_messages_in_windows(
            windows_ns=_read_windows_ns(
                lidars=lidars, cameras=cameras, camera_starts_ns=camera_starts_ns
            )
        )
        return _decode_payloads(
            session=session,
            reader=reader,
            recording_id=tick.recording_id,
            uri=recording.uri,
            lidars=lidars,
            cameras=cameras,
            camera_starts_ns=camera_starts_ns,
            messages=messages,
            target_frame_id=target_frame_id,
            camera_height=camera_height,
        )


def _read_windows_ns(
    lidars: Sequence[McapTable],
    cameras: Sequence[McapTable],
    camera_starts_ns: Mapping[int, int | None],
) -> dict[int, tuple[int, int]]:
    """Returns the log time window to decode per channel.

    A camera with a cached JPEG has no window.
    """
    windows_ns = {lidar.channel_id: (lidar.log_time_ns, lidar.log_time_ns) for lidar in lidars}
    for camera in cameras:
        start_ns = camera_starts_ns[camera.channel_id]
        if start_ns is not None:
            windows_ns[camera.channel_id] = (start_ns, camera.log_time_ns)
    return windows_ns


def _decode_payloads(  # noqa: PLR0913
    session: Session,
    reader: McapFileReader,
    recording_id: UUID,
    uri: str,
    lidars: Sequence[McapTable],
    cameras: Sequence[McapTable],
    camera_starts_ns: Mapping[int, int | None],
    messages: Mapping[int, Sequence[DecodedMessage]],
    target_frame_id: str | None,
    camera_height: int | None,
) -> list[TickPayload]:
    """Encodes the point clouds on this thread and the camera JPEGs in parallel."""
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

    def encode(camera: McapTable) -> bytes | None:
        return get_camera_frame.camera_jpeg(
            uri=uri,
            channel_id=camera.channel_id,
            keyframe_log_time_ns=_keyframe_ns(camera=camera),
            messages=messages.get(camera.channel_id, []),
            target_time_ns=camera.log_time_ns,
            height=camera_height,
        )

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(encode, camera) for camera in cameras]
        # Point clouds use the database session, so they stay on this thread.
        point_clouds = _point_cloud_payloads(
            session=session,
            reader=reader,
            recording_id=recording_id,
            lidars=lidars,
            messages=messages,
            target_frame_id=target_frame_id,
        )
        jpegs = [future.result() for future in futures]
    return point_clouds + _camera_payloads(
        reader=reader,
        uri=uri,
        cameras=cameras,
        camera_starts_ns=camera_starts_ns,
        jpegs=jpegs,
        camera_height=camera_height,
    )


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


def _camera_payloads(  # noqa: PLR0913
    reader: McapFileReader,
    uri: str,
    cameras: Sequence[McapTable],
    camera_starts_ns: Mapping[int, int | None],
    jpegs: Sequence[bytes | None],
    camera_height: int | None,
) -> list[TickPayload]:
    """Returns the camera payloads in request order, without channels with no frame.

    A camera without a JPEG whose read started after its keyframe reads again from
    the keyframe, see `get_camera_frame.camera_read_start_ns`.
    """
    payloads = []
    for camera, jpeg in zip(cameras, jpegs):
        data = jpeg
        if data is None and camera_starts_ns[camera.channel_id] != _keyframe_ns(camera=camera):
            data = get_camera_frame.camera_jpeg_from_keyframe(
                reader=reader,
                uri=uri,
                channel_id=camera.channel_id,
                keyframe_log_time_ns=_keyframe_ns(camera=camera),
                target_time_ns=camera.log_time_ns,
                height=camera_height,
            )
        if data is None:
            logger.warning(
                "Camera channel %s has no frame at %s.", camera.channel_id, camera.log_time_ns
            )
            continue
        payloads.append(
            TickPayload(
                channel_id=camera.channel_id,
                kind=TickPayloadKind.CAMERA_JPEG,
                log_time_ns=camera.log_time_ns,
                data=data,
            )
        )
    return payloads


def _keyframe_ns(camera: McapTable) -> int:
    """Returns the keyframe log time of a camera locator."""
    assert camera.keyframe_log_time_ns is not None
    return camera.keyframe_log_time_ns


def _message_at(messages: Sequence[DecodedMessage], log_time_ns: int) -> DecodedMessage | None:
    """Returns the message at an exact log time."""
    return next((message for message in messages if message.log_time_ns == log_time_ns), None)
