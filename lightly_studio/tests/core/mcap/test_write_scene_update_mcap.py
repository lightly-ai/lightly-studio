from __future__ import annotations

from pathlib import Path

from mcap import reader as mcap_reader
from mcap.well_known import MessageEncoding, SchemaEncoding

from lightly_studio.core.mcap import add_labels, write_scene_update_mcap
from lightly_studio.core.mcap.scene_update_schema import SCENE_UPDATE_SCHEMA_NAME
from lightly_studio.core.mcap.type_definitions import CuboidLabel, SceneUpdateLabels

TOPIC = "/det"
METADATA_RECORDS = [("rosbag2", {"serialized_metadata": "version: 9"})]


def _cuboid() -> CuboidLabel:
    return CuboidLabel(
        timestamp_ns=2_000,
        frame_id="odom",
        class_name="truck",
        track_id=1,
        parent_track_id=None,
        interpolated=False,
        position=(1.0, 2.0, 0.5),
        rotation=(0.0, 0.0, 0.0, 1.0),
        size=(2.0, 1.0, 1.5),
    )


def _messages() -> list[tuple[int, SceneUpdateLabels]]:
    return [
        (2_000, SceneUpdateLabels(cuboids=(_cuboid(),))),
        (3_000, SceneUpdateLabels(cuboids=())),
    ]


def test_write_scene_update_mcap__readable_by_import(tmp_path: Path) -> None:
    path = tmp_path / "foo_labeled.mcap"

    with path.open("wb") as output:
        write_scene_update_mcap.write_scene_update_mcap(
            output=output,
            messages=_messages(),
            frame_id="odom",
            topic=TOPIC,
            metadata_records=METADATA_RECORDS,
        )

    result = add_labels.read_scene_updates(annotation_mcap_uri=str(path), topic=TOPIC)

    assert [log_time for log_time, _ in result] == [2_000, 3_000]
    assert result[0][1].cuboids[0].track_id == 1
    assert result[1][1].cuboids == ()


def test_write_scene_update_mcap__header_schema_and_metadata(tmp_path: Path) -> None:
    path = tmp_path / "foo_labeled.mcap"

    with path.open("wb") as output:
        write_scene_update_mcap.write_scene_update_mcap(
            output=output,
            messages=_messages(),
            frame_id="odom",
            topic=TOPIC,
            metadata_records=METADATA_RECORDS,
        )

    with path.open("rb") as stream:
        reader = mcap_reader.make_reader(stream=stream)
        assert reader.get_header().profile == "ros2"

        summary = reader.get_summary()
        assert summary is not None
        schemas = list(summary.schemas.values())
        assert len(schemas) == 1
        assert schemas[0].name == SCENE_UPDATE_SCHEMA_NAME
        assert schemas[0].encoding == SchemaEncoding.ROS2

        channels = list(summary.channels.values())
        assert len(channels) == 1
        assert channels[0].message_encoding == MessageEncoding.CDR

        for _, _, message in reader.iter_messages():
            assert message.publish_time == message.log_time

        records = [(record.name, dict(record.metadata)) for record in reader.iter_metadata()]
        assert records == METADATA_RECORDS
