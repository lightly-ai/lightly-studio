from __future__ import annotations

import pytest

from lightly_studio.core.mcap import topic_kind
from lightly_studio.core.mcap.topic_kind import TopicKind


@pytest.mark.parametrize(
    ("schema_name", "expected"),
    [
        ("foxglove.CompressedVideo", TopicKind.VIDEO),
        ("foxglove_msgs/msg/CompressedVideo", TopicKind.VIDEO),
        ("sensor_msgs/msg/CompressedImage", TopicKind.IMAGE),
        ("foxglove.RawImage", TopicKind.IMAGE),
        ("sensor_msgs/msg/PointCloud2", TopicKind.POINT_CLOUD),
        ("foxglove.PointCloud", TopicKind.POINT_CLOUD),
        ("sensor_msgs/msg/CameraInfo", TopicKind.CAMERA_INFO),
        ("foxglove.CameraCalibration", TopicKind.CAMERA_INFO),
        ("tf2_msgs/msg/TFMessage", TopicKind.TRANSFORM),
        ("foxglove.FrameTransforms", TopicKind.TRANSFORM),
        ("foxglove.SceneUpdate", TopicKind.SCENE_UPDATE),
        ("foxglove_msgs/msg/SceneUpdate", TopicKind.SCENE_UPDATE),
        ("sensor_msgs/msg/Imu", TopicKind.OTHER),
        ("", TopicKind.OTHER),
    ],
)
def test_from_schema_name(schema_name: str, expected: TopicKind) -> None:
    assert topic_kind.from_schema_name(schema_name) == expected


def test_from_schema_name__no_schema() -> None:
    assert topic_kind.from_schema_name(None) == TopicKind.OTHER


def test_message_type() -> None:
    assert topic_kind._message_type("foxglove_msgs/msg/CompressedVideo") == "CompressedVideo"
    assert topic_kind._message_type("foxglove.CompressedVideo") == "CompressedVideo"
    assert topic_kind._message_type("CompressedVideo") == "CompressedVideo"
