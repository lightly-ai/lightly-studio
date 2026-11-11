"""Writes cuboid labels as a Foxglove SceneUpdate annotation file."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import IO

from mcap_ros2.writer import Writer as Ros2Writer

from lightly_studio.core.mcap import scene_update, scene_update_schema
from lightly_studio.core.mcap.type_definitions import SceneUpdateLabels


def write_scene_update_mcap(
    output: IO[bytes],
    messages: Sequence[tuple[int, SceneUpdateLabels]],
    frame_id: str,
    topic: str,
    metadata_records: Sequence[tuple[str, Mapping[str, str]]],
) -> None:
    """Writes a SceneUpdate annotation file.

    Args:
        output: The binary stream to write the MCAP to.
        messages: `(log_time_ns, labels)` pairs, in file order. Both the message log
            time and publish time are `log_time_ns`.
        frame_id: The coordinate frame of every entity, forwarded to `to_message`.
        topic: The topic to write the messages on.
        metadata_records: `(name, data)` pairs, copied into the file as Metadata
            records, in order.
    """
    with Ros2Writer(output=output) as writer:
        schema = writer.register_msgdef(
            datatype=scene_update_schema.SCENE_UPDATE_SCHEMA_NAME,
            msgdef_text=scene_update_schema.SCENE_UPDATE_MSGDEF,
        )
        for name, data in metadata_records:
            writer.add_metadata(name=name, data=dict(data))
        for log_time, labels in messages:
            writer.write_message(
                topic=topic,
                schema=schema,
                message=scene_update.to_message(labels=labels, frame_id=frame_id),
                log_time=log_time,
                publish_time=log_time,
            )
