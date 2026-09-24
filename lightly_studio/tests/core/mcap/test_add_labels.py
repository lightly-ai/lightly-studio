from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from lightly_studio.core.mcap import add_labels
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.sequence import McapSequenceEntry
from lightly_studio.core.mcap.type_definitions import CuboidLabel, FrameTags, SceneUpdateLabels
from tests.core.mcap import helpers

TIMESTAMP_NS = helpers.LIDAR_LOG_TIMES_NS[0]
SCENE_UPDATE_SCHEMA = "foxglove_msgs/msg/SceneUpdate"
SCENE_UPDATE_TOPIC = "/scene_update"


def _cuboid(timestamp_ns: int = TIMESTAMP_NS, track_id: int = 1, px: float = 4.0) -> CuboidLabel:
    return CuboidLabel(
        timestamp_ns=timestamp_ns,
        frame_id="odom",
        class_name="truck",
        track_id=track_id,
        parent_track_id=None,
        interpolated=False,
        position=(px, 0.0, 0.5),
        rotation=(0.0, 0.0, 0.0, 1.0),
        size=(2.0, 1.0, 1.5),
    )


def test_match_labels__joins_cuboid_to_tick() -> None:
    group_id = uuid4()
    ticks = {TIMESTAMP_NS: group_id}
    messages = [(TIMESTAMP_NS, SceneUpdateLabels(cuboids=(_cuboid(),)))]

    matched = add_labels.match_labels(messages=messages, ticks=ticks)

    assert matched.matched_count == 1
    assert matched.unmatched_count == 0
    assert matched.cuboids_by_group[group_id][0].track_id == 1


def test_match_labels__unmatched_entity(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("WARNING")
    group_id = uuid4()
    ticks = {TIMESTAMP_NS: group_id}
    messages = [(TIMESTAMP_NS, SceneUpdateLabels(cuboids=(_cuboid(timestamp_ns=9_999_000_000),)))]

    matched = add_labels.match_labels(messages=messages, ticks=ticks)
    add_labels.log_match_summary(
        annotation_mcap_uri="memory://foo_labeled.mcap",
        matched=matched,
        ticks=ticks,
        messages=messages,
    )

    assert matched.matched_count == 0
    assert matched.unmatched_count == 1
    assert matched.cuboids_by_group == {}
    assert "Clock mismatch" in caplog.text
    assert "first ticks" in caplog.text
    assert str(TIMESTAMP_NS) in caplog.text


def test_match_labels__empty_scene_uses_log_time() -> None:
    group_id = uuid4()
    ticks = {TIMESTAMP_NS: group_id}
    messages = [(TIMESTAMP_NS, SceneUpdateLabels(cuboids=()))]

    matched = add_labels.match_labels(messages=messages, ticks=ticks)

    assert matched.empty_group_ids == {group_id}
    assert matched.matched_count == 1


def test_match_labels__empty_scene_uses_entity_clock_offset() -> None:
    first_group_id = uuid4()
    second_group_id = uuid4()
    log_time_ns = 1_000
    offset_ns = TIMESTAMP_NS - log_time_ns
    empty_scene_log_time_ns = log_time_ns + 1_000_000_000
    clock_variation_ns = 5_000_000
    messages = [
        (log_time_ns, SceneUpdateLabels(cuboids=(_cuboid(timestamp_ns=TIMESTAMP_NS),))),
        (empty_scene_log_time_ns, SceneUpdateLabels(cuboids=())),
    ]
    ticks = {
        TIMESTAMP_NS: first_group_id,
        empty_scene_log_time_ns + offset_ns + clock_variation_ns: second_group_id,
    }

    matched = add_labels.match_labels(messages=messages, ticks=ticks)

    assert matched.empty_group_ids == {second_group_id}
    assert matched.matched_count == 2


def test_match_labels__empty_scene_outside_tolerance_is_unmatched() -> None:
    group_id = uuid4()
    log_time_ns = 1_000
    offset_ns = TIMESTAMP_NS - log_time_ns
    empty_scene_log_time_ns = log_time_ns + 1_000_000_000
    messages = [
        (log_time_ns, SceneUpdateLabels(cuboids=(_cuboid(timestamp_ns=TIMESTAMP_NS),))),
        (empty_scene_log_time_ns, SceneUpdateLabels(cuboids=())),
    ]
    ticks = {
        TIMESTAMP_NS: group_id,
        empty_scene_log_time_ns
        + offset_ns
        + add_labels.DEFAULT_EMPTY_SCENE_MAX_DIFF_NS
        + 1: uuid4(),
    }

    matched = add_labels.match_labels(messages=messages, ticks=ticks)

    assert matched.empty_group_ids == set()
    assert matched.matched_count == 1
    assert matched.unmatched_count == 1


def test_match_labels__frame_tags() -> None:
    group_id = uuid4()
    ticks = {TIMESTAMP_NS: group_id}
    frame_tags = FrameTags(timestamp_ns=TIMESTAMP_NS, tags=("lidar_dropout",), note="sparse")
    messages = [(TIMESTAMP_NS, SceneUpdateLabels(cuboids=(), frame_tags=frame_tags))]

    matched = add_labels.match_labels(messages=messages, ticks=ticks)

    assert matched.tags_by_group[group_id] is frame_tags
    assert matched.matched_count == 1


def test_match_labels__duplicate_frame_tags() -> None:
    group_id = uuid4()
    ticks = {TIMESTAMP_NS: group_id}
    frame_tags = FrameTags(timestamp_ns=TIMESTAMP_NS, tags=("lidar_dropout",), note=None)
    messages = [
        (TIMESTAMP_NS, SceneUpdateLabels(cuboids=(), frame_tags=frame_tags)),
        (TIMESTAMP_NS, SceneUpdateLabels(cuboids=(), frame_tags=frame_tags)),
    ]

    with pytest.raises(McapAccessError, match="Multiple frame tag entities"):
        add_labels.match_labels(messages=messages, ticks=ticks)


def test_ticks_by_timestamp__drops_missing_time() -> None:
    group_id = uuid4()
    entries = [
        McapSequenceEntry(sample_id=group_id, seq_number=0, timestamp_ns=TIMESTAMP_NS),
        McapSequenceEntry(sample_id=uuid4(), seq_number=1, timestamp_ns=None),
    ]

    ticks = add_labels.ticks_by_timestamp(entries=entries)

    assert ticks == {TIMESTAMP_NS: group_id}


def test_ticks_by_timestamp__duplicate_timestamp() -> None:
    entries = [
        McapSequenceEntry(sample_id=uuid4(), seq_number=0, timestamp_ns=TIMESTAMP_NS),
        McapSequenceEntry(sample_id=uuid4(), seq_number=1, timestamp_ns=TIMESTAMP_NS),
    ]

    with pytest.raises(ValueError, match="multiple ticks"):
        add_labels.ticks_by_timestamp(entries=entries)


def test_read_scene_updates(tmp_path: Path) -> None:
    path = helpers.write_json_mcap(
        path=tmp_path / "foo_labeled.mcap",
        topic=SCENE_UPDATE_TOPIC,
        schema_name=SCENE_UPDATE_SCHEMA,
        messages=[
            (
                TIMESTAMP_NS,
                {
                    "entities": [
                        {
                            "id": "truck_1",
                            "timestamp": {
                                "sec": TIMESTAMP_NS // 1_000_000_000,
                                "nsec": TIMESTAMP_NS % 1_000_000_000,
                            },
                            "frame_id": "odom",
                            "metadata": [
                                {"key": "class", "value": "truck"},
                                {"key": "track_id", "value": "7"},
                            ],
                            "cubes": [
                                {
                                    "pose": {
                                        "position": {"x": 4.0, "y": 0.0, "z": 0.5},
                                        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                                    },
                                    "size": {"x": 2.0, "y": 1.0, "z": 1.5},
                                }
                            ],
                        }
                    ]
                },
            )
        ],
    )

    messages = add_labels.read_scene_updates(
        annotation_mcap_uri=str(path),
        topic=SCENE_UPDATE_TOPIC,
    )

    assert len(messages) == 1
    log_time_ns, labels = messages[0]
    assert log_time_ns == TIMESTAMP_NS
    assert labels.cuboids[0].track_id == 7
    assert labels.cuboids[0].timestamp_ns == TIMESTAMP_NS
