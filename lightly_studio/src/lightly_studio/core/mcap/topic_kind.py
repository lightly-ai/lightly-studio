"""Classification of MCAP topics by the message type they carry."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum


class TopicKind(str, Enum):
    """The kind of data a topic carries.

    Callers use the kind to decide how a topic can be interpreted, for example
    whether its frame locators can carry keyframe times.
    """

    VIDEO = "video"
    IMAGE = "image"
    POINT_CLOUD = "point_cloud"
    CAMERA_INFO = "camera_info"
    TRANSFORM = "transform"
    OTHER = "other"


# The message types we recognize, keyed by their bare type name. The same message
# exists under several schema names, e.g. `sensor_msgs/msg/CameraInfo` for ros2msg
# and `foxglove.CameraCalibration` for protobuf, so the bare name is what we match.
_KIND_BY_MESSAGE_TYPE: Mapping[str, TopicKind] = {
    "CompressedVideo": TopicKind.VIDEO,
    "CompressedImage": TopicKind.IMAGE,
    "Image": TopicKind.IMAGE,
    "RawImage": TopicKind.IMAGE,
    "PointCloud": TopicKind.POINT_CLOUD,
    "PointCloud2": TopicKind.POINT_CLOUD,
    "CameraInfo": TopicKind.CAMERA_INFO,
    "CameraCalibration": TopicKind.CAMERA_INFO,
    "TFMessage": TopicKind.TRANSFORM,
    "FrameTransform": TopicKind.TRANSFORM,
    "FrameTransforms": TopicKind.TRANSFORM,
    "TransformStamped": TopicKind.TRANSFORM,
}


def from_schema_name(schema_name: str | None) -> TopicKind:
    """Returns the kind of topic that carries messages of a schema.

    Args:
        schema_name: The schema name as recorded in the MCAP file, e.g.
            `sensor_msgs/msg/PointCloud2`. `None` for a channel without a schema.

    Returns:
        The kind of the topic, or `TopicKind.OTHER` for an unknown message type.
    """
    if schema_name is None:
        return TopicKind.OTHER
    return _KIND_BY_MESSAGE_TYPE.get(_message_type(schema_name), TopicKind.OTHER)


def _message_type(schema_name: str) -> str:
    """Returns the bare message type name of a schema name.

    Args:
        schema_name: A namespaced schema name, e.g. `foxglove.CompressedVideo` or
            `foxglove_msgs/msg/CompressedVideo`.

    Returns:
        The last component of the name, e.g. `CompressedVideo`.
    """
    return schema_name.replace(".", "/").rsplit("/", maxsplit=1)[-1]
