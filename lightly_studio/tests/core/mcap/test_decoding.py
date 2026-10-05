from __future__ import annotations

from pathlib import Path

from mcap.records import Schema
from mcap.well_known import MessageEncoding, SchemaEncoding
from mcap.writer import Writer as RawWriter
from mcap_ros2._dynamic import serialize_dynamic

from lightly_studio.core.mcap import decoding
from lightly_studio.core.mcap.reader import McapFileReader


def test_rewrite_ros1_time_types() -> None:
    schema_text = "time timestamp\nduration lifetime\nstring frame_id\n"

    assert decoding._rewrite_ros1_time_types(schema_text=schema_text) == (
        "builtin_interfaces/Time timestamp\nbuiltin_interfaces/Duration lifetime\nstring frame_id\n"
    )


def test_rewrite_ros1_time_types__arrays_and_indentation() -> None:
    schema_text = "time[] stamps\n  duration lifetime\n"

    assert decoding._rewrite_ros1_time_types(schema_text=schema_text) == (
        "builtin_interfaces/Time[] stamps\n  builtin_interfaces/Duration lifetime\n"
    )


def test_rewrite_ros1_time_types__unchanged() -> None:
    schema_text = "builtin_interfaces/Time timestamp\nstring timezone\n"

    assert decoding._rewrite_ros1_time_types(schema_text=schema_text) == schema_text


def test_ros2_decoder_factory__time_fields() -> None:
    schema_text = "time timestamp\nduration lifetime\nstring frame_id\n"
    payload = _encode_cdr(
        schema_text=schema_text,
        message={
            "timestamp": {"sec": 1, "nanosec": 500_000_000},
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
            data=schema_text.encode(),
        ),
    )

    assert decoder is not None
    decoded = decoder(payload)
    assert decoded.timestamp.sec == 1
    assert decoded.timestamp.nanosec == 500_000_000
    assert decoded.lifetime.sec == 0
    assert decoded.lifetime.nanosec == 150_000_000
    assert decoded.frame_id == "odom"


def test_get_decoded_message_at__ros1_time_fields(tmp_path: Path) -> None:
    schema_text = "time timestamp\nstring frame_id\n"
    payload = _encode_cdr(
        schema_text=schema_text,
        message={"timestamp": {"sec": 2, "nanosec": 250_000_000}, "frame_id": "base_link"},
    )
    path = tmp_path / "stamp.mcap"
    with path.open("wb") as stream:
        writer = RawWriter(output=stream)
        writer.start()
        schema_id = writer.register_schema(
            name="test_msgs/msg/Stamp",
            encoding=SchemaEncoding.ROS2,
            data=schema_text.encode(),
        )
        channel_id = writer.register_channel(
            topic="/stamp", message_encoding=MessageEncoding.CDR, schema_id=schema_id
        )
        writer.add_message(channel_id=channel_id, log_time=1000, publish_time=1000, data=payload)
        writer.finish()

    with McapFileReader(path) as reader:
        message = reader.get_decoded_message_at(channel_id=channel_id, timestamp_ns=1000)

    assert message is not None
    assert message.log_time_ns == 1000
    assert message.decoded_message.timestamp.sec == 2
    assert message.decoded_message.timestamp.nanosec == 250_000_000
    assert message.decoded_message.frame_id == "base_link"


def _encode_cdr(schema_text: str, message: dict[str, object]) -> bytes:
    """Encodes a message with builtin Time and Duration types in place of ROS 1 types."""
    schema_name = "test_msgs/msg/Stamp"
    rewritten = decoding._rewrite_ros1_time_types(schema_text=schema_text)
    encoder = serialize_dynamic(schema_name, rewritten)[schema_name]
    return encoder(message)
