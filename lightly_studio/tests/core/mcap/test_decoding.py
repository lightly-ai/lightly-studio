from __future__ import annotations

from pathlib import Path

from mcap.records import Schema
from mcap.well_known import MessageEncoding, SchemaEncoding
from mcap.writer import Writer as RawWriter
from mcap_ros2._dynamic import serialize_dynamic

from lightly_studio.core.mcap import decoding, scene_update
from lightly_studio.core.mcap.reader import McapFileReader

SCENE_UPDATE_TOPIC = "/gt/scene_update"
SCENE_UPDATE_SCHEMA_NAME = "foxglove_msgs/msg/SceneUpdate"
TIMESTAMP_SEC = 1
TIMESTAMP_NANOSEC = 500_000_000
TIMESTAMP_NS = TIMESTAMP_SEC * 1_000_000_000 + TIMESTAMP_NANOSEC
LOG_TIME_NS = 1_000_000_000

_STAMP_ROS1_MSGDEF = """
time timestamp
duration lifetime
string frame_id
"""

_SCENE_UPDATE_ROS1_MSGDEF = """
foxglove_msgs/SceneEntity[] entities
================================================================================
MSG: foxglove_msgs/SceneEntity
time timestamp
string frame_id
string id
duration lifetime
bool frame_locked
foxglove_msgs/KeyValuePair[] metadata
foxglove_msgs/CubePrimitive[] cubes
================================================================================
MSG: foxglove_msgs/KeyValuePair
string key
string value
================================================================================
MSG: foxglove_msgs/CubePrimitive
foxglove_msgs/Pose pose
foxglove_msgs/Vector3 size
================================================================================
MSG: foxglove_msgs/Pose
foxglove_msgs/Vector3 position
foxglove_msgs/Quaternion orientation
================================================================================
MSG: foxglove_msgs/Vector3
float64 x
float64 y
float64 z
================================================================================
MSG: foxglove_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w
"""


def test_rewrite_ros1_time_types() -> None:
    rewritten = decoding._rewrite_ros1_time_types(schema_text=_STAMP_ROS1_MSGDEF)

    assert rewritten == (
        "\nbuiltin_interfaces/Time timestamp\n"
        "builtin_interfaces/Duration lifetime\n"
        "string frame_id\n"
    )


def test_rewrite_ros1_time_types__already_builtin() -> None:
    schema_text = "builtin_interfaces/Time timestamp\n"
    assert decoding._rewrite_ros1_time_types(schema_text=schema_text) == schema_text


def test_rewrite_ros1_time_types__nested_and_arrays() -> None:
    schema_text = "time[] stamps\n  duration lifetime\n"
    rewritten = decoding._rewrite_ros1_time_types(schema_text=schema_text)

    assert rewritten == "builtin_interfaces/Time[] stamps\n  builtin_interfaces/Duration lifetime\n"


def test_ros2_decoder_factory__time_fields() -> None:
    payload = _encode_cdr(
        schema_name="test_msgs/msg/Stamp",
        schema_text=_STAMP_ROS1_MSGDEF,
        message={
            "timestamp": {"sec": TIMESTAMP_SEC, "nanosec": TIMESTAMP_NANOSEC},
            "lifetime": {"sec": 0, "nanosec": 150_000_000},
            "frame_id": "odom",
        },
    )
    decoder = decoding.Ros2DecoderFactory().decoder_for(
        message_encoding=MessageEncoding.CDR,
        schema=Schema(
            id=1,
            name="test_msgs/msg/Stamp",
            encoding=SchemaEncoding.ROS2,
            data=_STAMP_ROS1_MSGDEF.encode(),
        ),
    )

    assert decoder is not None
    decoded = decoder(payload)
    assert decoded.timestamp.sec == TIMESTAMP_SEC
    assert decoded.timestamp.nanosec == TIMESTAMP_NANOSEC
    assert decoded.lifetime.sec == 0
    assert decoded.lifetime.nanosec == 150_000_000
    assert decoded.frame_id == "odom"


def test_get_decoded_message_at__ros1_time_scene_update(tmp_path: Path) -> None:
    path = _write_scene_update_with_ros1_time(path=tmp_path / "labeled.mcap")

    with McapFileReader(path) as reader:
        channel_id = next(
            topic.channel_id for topic in reader.get_topics() if topic.name == SCENE_UPDATE_TOPIC
        )
        message = reader.get_decoded_message_at(channel_id=channel_id, timestamp_ns=LOG_TIME_NS)

    assert message is not None
    assert message.log_time_ns == LOG_TIME_NS
    labels = scene_update.from_decoded_message(message.decoded_message)
    assert labels.frame_tags is None
    assert len(labels.cuboids) == 1
    cuboid = labels.cuboids[0]
    assert cuboid.timestamp_ns == TIMESTAMP_NS
    assert cuboid.frame_id == "odom"
    assert cuboid.class_name == "truck"
    assert cuboid.track_id == 3
    assert cuboid.position == (12.41, -3.08, 1.62)
    assert cuboid.size == (5.2, 2.44, 1.15)


def _encode_cdr(schema_name: str, schema_text: str, message: object) -> bytes:
    """Encodes a message with the rewritten schema so CDR matches builtin Time."""
    rewritten = decoding._rewrite_ros1_time_types(schema_text=schema_text)
    encoder = serialize_dynamic(schema_name, rewritten)[schema_name]
    return encoder(message)


def _write_scene_update_with_ros1_time(path: Path) -> Path:
    """Writes a SceneUpdate MCAP whose schema still uses ROS 1 `time`/`duration`."""
    payload = _encode_cdr(
        schema_name=SCENE_UPDATE_SCHEMA_NAME,
        schema_text=_SCENE_UPDATE_ROS1_MSGDEF,
        message=_scene_update_message(),
    )
    with path.open("wb") as stream:
        writer = RawWriter(output=stream)
        writer.start()
        schema_id = writer.register_schema(
            name=SCENE_UPDATE_SCHEMA_NAME,
            encoding=SchemaEncoding.ROS2,
            data=_SCENE_UPDATE_ROS1_MSGDEF.encode(),
        )
        channel_id = writer.register_channel(
            topic=SCENE_UPDATE_TOPIC, message_encoding=MessageEncoding.CDR, schema_id=schema_id
        )
        writer.add_message(
            channel_id=channel_id,
            log_time=LOG_TIME_NS,
            publish_time=LOG_TIME_NS,
            data=payload,
        )
        writer.finish()
    return path


def _scene_update_message() -> dict[str, object]:
    return {
        "entities": [
            {
                "timestamp": {"sec": TIMESTAMP_SEC, "nanosec": TIMESTAMP_NANOSEC},
                "frame_id": "odom",
                "id": "truck_3",
                "lifetime": {"sec": 0, "nanosec": 0},
                "frame_locked": False,
                "metadata": [
                    {"key": "class", "value": "truck"},
                    {"key": "track_id", "value": "3"},
                    {"key": "parent_track_id", "value": ""},
                    {"key": "interpolated", "value": "false"},
                ],
                "cubes": [
                    {
                        "pose": {
                            "position": {"x": 12.41, "y": -3.08, "z": 1.62},
                            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                        },
                        "size": {"x": 5.2, "y": 2.44, "z": 1.15},
                    }
                ],
            }
        ]
    }
