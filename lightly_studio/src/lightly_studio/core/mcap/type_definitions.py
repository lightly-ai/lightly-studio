"""Value types returned by the MCAP access layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lightly_studio.core.mcap.topic_kind import TopicKind


@dataclass(frozen=True)
class TopicInfo:
    """A topic recorded in an MCAP file.

    Attributes:
        name: The topic name, e.g. `/cam/front/compressed_video`.
        channel_id: The id of the channel that carries the topic.
        message_encoding: How the message payloads are encoded, e.g. `cdr`.
        schema_name: The name of the message schema, `None` without a schema.
        schema_encoding: How the schema is encoded, e.g. `ros2msg`, `None` without a schema.
        kind: The kind of data the topic carries.
        message_count: The number of messages on the topic, `None` if the file does not
            report statistics.
    """

    name: str
    channel_id: int
    message_encoding: str
    schema_name: str | None
    schema_encoding: str | None
    kind: TopicKind
    message_count: int | None


@dataclass(frozen=True)
class FrameLocator:
    """Points at a single message in an MCAP file without carrying its payload.

    Attributes:
        channel_id: The id of the channel the message belongs to.
        log_time_ns: The time the message was logged, in nanoseconds. Used to seek
            the payload in the file.
        capture_timestamp_ns: The sensor capture time from `header.stamp` or
            `timestamp`, in nanoseconds.
        topic: The topic the message was logged on.
        keyframe_log_time_ns: For video, the log time of the latest keyframe at or
            before this frame, which is where decoding has to start. `None` for topics
            that are not video, and for frames that no keyframe precedes.
        schema_name: The name of the message schema, `None` without a schema.
    """

    channel_id: int
    log_time_ns: int
    capture_timestamp_ns: int
    topic: str
    keyframe_log_time_ns: int | None = None
    schema_name: str | None = None


@dataclass(frozen=True)
class CameraIntrinsics:
    """The intrinsic calibration of a camera.

    Attributes:
        width: The image width in pixels.
        height: The image height in pixels.
        camera_matrix: The 3x3 camera matrix K in row-major order, 9 values.
        frame_id: The coordinate frame of the camera, `None` if the message omits it.
        distortion_model: The distortion model, e.g. `plumb_bob`, `None` if the message
            omits it.
        distortion_coefficients: The distortion coefficients D. Empty if the message
            omits them.
    """

    width: int
    height: int
    camera_matrix: tuple[float, ...]
    frame_id: str | None
    distortion_model: str | None = None
    distortion_coefficients: tuple[float, ...] = ()


@dataclass(frozen=True)
class DecodedMessage:
    """A single decoded message read off a channel.

    Attributes:
        channel_id: The id of the channel the message was read from.
        topic: The topic the channel is recorded on.
        log_time_ns: The time the message was logged, in nanoseconds.
        schema_name: The name of the message schema, `None` without a schema.
        decoded_message: The decoded payload, shaped by the message's encoding (a ROS
            2 message object, a protobuf object, or a plain dict for JSON).
    """

    channel_id: int
    topic: str
    log_time_ns: int
    schema_name: str | None
    decoded_message: Any


@dataclass(frozen=True)
class StaticTransform:
    """A static transform between two coordinate frames.

    The transform maps points from the child frame to the parent frame.

    Attributes:
        parent_frame_id: The frame the transform maps points to.
        child_frame_id: The frame the transform maps points from.
        translation: The translation as (x, y, z) in meters.
        rotation: The rotation as a quaternion (x, y, z, w).
        log_time_ns: The time the transform was logged, in nanoseconds.
    """

    parent_frame_id: str
    child_frame_id: str
    translation: tuple[float, float, float]
    rotation: tuple[float, float, float, float]
    log_time_ns: int


@dataclass(frozen=True)
class CuboidLabel:
    """A 9-DoF cuboid decoded from one SceneEntity in a SceneUpdate.

    Attributes:
        timestamp_ns: The lidar sweep time of the frame, in nanoseconds.
        frame_id: The coordinate frame the pose is expressed in, e.g. `odom`.
        class_name: The annotation class, e.g. `truck_bed`.
        track_id: The vendor track id of this box.
        parent_track_id: The vendor track id of the parent truck, or `None`.
        interpolated: Whether the box was interpolated between keyframes.
        position: The cuboid centre as (x, y, z) in metres.
        rotation: The orientation as a quaternion (x, y, z, w).
        size: The full extents as (length, width, height) in metres.
    """

    timestamp_ns: int
    frame_id: str
    class_name: str
    track_id: int
    parent_track_id: int | None
    interpolated: bool
    position: tuple[float, float, float]
    rotation: tuple[float, float, float, float]
    size: tuple[float, float, float]


@dataclass(frozen=True)
class FrameTags:
    """Frame-level tags carried on the metadata-only `id=frame` SceneEntity.

    Attributes:
        timestamp_ns: The lidar sweep time of the frame, in nanoseconds.
        tags: Tag names present on the frame, e.g. `lidar_dropout`.
        note: Free-text note, typically for `ambiguous_object`. `None` if omitted.
    """

    timestamp_ns: int
    tags: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True)
class SceneUpdateLabels:
    """The cuboids and optional frame tags decoded from one SceneUpdate message.

    An empty `cuboids` tuple and no `frame_tags` is a valid empty scene. The
    payload then has no entity timestamp; the caller uses the message log time.
    """

    cuboids: tuple[CuboidLabel, ...]
    frame_tags: FrameTags | None = None
