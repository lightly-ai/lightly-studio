from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from lightly_studio.core.mcap import add_labels, add_mcaps
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.core.mcap.sequence import McapSequence
from lightly_studio.core.mcap.type_definitions import CuboidLabel, SceneUpdateLabels
from lightly_studio.database import db_manager
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.core.mcap import helpers

POINT_CLOUD_COMPONENT = "pcl_front"
MAX_PAIRING_DIFF_NS = 50_000_000
COMPONENTS = [
    McapComponentSpec(
        name="front",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic=helpers.CAMERA_VIDEO_TOPIC,
        camera_info_topic=helpers.CAMERA_INFO_TOPIC,
    ),
    McapComponentSpec(
        name=POINT_CLOUD_COMPONENT,
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic=helpers.LIDAR_POINTS_TOPIC,
        frame_id=helpers.LIDAR_FRAME_ID,
    ),
]


def test_write_sequence_labels(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, group_ids = _index_recording(tmp_path=tmp_path)
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    messages = [
        (
            timestamp_ns + 10_000_000,
            SceneUpdateLabels(cuboids=(_cuboid(timestamp_ns=timestamp_ns, track_id=7, px=4.0),)),
        )
    ]

    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://foo_labeled.mcap",
        messages=messages,
    )

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert len(annotations) == 1
    assert annotations[0].parent_sample_id == group_ids[0]
    assert annotations[0].cuboid_3d_details is not None
    assert annotations[0].cuboid_3d_details.px == pytest.approx(4.0)
    assert annotations[0].annotation_label.annotation_label_name == "truck"
    assert annotations[0].object_track_id is not None
    track = object_track_resolver.get_by_id(
        session=db_manager.persistent_session(),
        object_track_id=annotations[0].object_track_id,
    )
    assert track is not None
    assert track.source_track_id == 7


def test_write_sequence_labels__links_parent_tracks(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = _index_recording(tmp_path=tmp_path)
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    # Track 8 has a parent with cuboids. Track 9 has a parent without cuboids.
    cuboids = (
        _cuboid(timestamp_ns=timestamp_ns, track_id=7),
        _cuboid(timestamp_ns=timestamp_ns, track_id=8, parent_track_id=7),
        _cuboid(timestamp_ns=timestamp_ns, track_id=9, parent_track_id=5),
    )

    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://foo_labeled.mcap",
        messages=[(timestamp_ns, SceneUpdateLabels(cuboids=cuboids))],
    )

    tracks = object_track_resolver.get_all_by_dataset_id(
        session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
    )
    by_source = {track.source_track_id: track for track in tracks}
    assert set(by_source) == {5, 7, 8, 9}
    assert by_source[5].parent_object_track_id is None
    assert by_source[7].parent_object_track_id is None
    assert by_source[8].parent_object_track_id == by_source[7].object_track_id
    assert by_source[9].parent_object_track_id == by_source[5].object_track_id
    assert sorted(track.object_track_number for track in tracks) == [1, 2, 3, 4]


def test_write_sequence_labels__conflicting_parent_tracks(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = _index_recording(tmp_path=tmp_path)
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    cuboids = (
        _cuboid(timestamp_ns=timestamp_ns, track_id=8, parent_track_id=7),
        _cuboid(timestamp_ns=timestamp_ns, track_id=8, parent_track_id=6),
    )

    with pytest.raises(ValueError, match="Track 8 has more than one parent track id"):
        add_labels.write_sequence_labels(
            dataset=dataset,
            sequence=sequence,
            annotation_mcap_uri="memory://foo_labeled.mcap",
            messages=[(timestamp_ns, SceneUpdateLabels(cuboids=cuboids))],
        )


def test_write_sequence_labels__parent_track_cycle(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = _index_recording(tmp_path=tmp_path)
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    # Track 1 is a root. Tracks 7 and 8 parent each other.
    cuboids = (
        _cuboid(timestamp_ns=timestamp_ns, track_id=1),
        _cuboid(timestamp_ns=timestamp_ns, track_id=7, parent_track_id=8),
        _cuboid(timestamp_ns=timestamp_ns, track_id=8, parent_track_id=7),
    )

    with pytest.raises(ValueError, match="A parent track must not have a parent track itself"):
        add_labels.write_sequence_labels(
            dataset=dataset,
            sequence=sequence,
            annotation_mcap_uri="memory://foo_labeled.mcap",
            messages=[(timestamp_ns, SceneUpdateLabels(cuboids=cuboids))],
        )

    tracks = object_track_resolver.get_all_by_dataset_id(
        session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
    )
    assert len(tracks) == 0


def _index_recording(tmp_path: Path) -> tuple[McapDataset, McapSequence, list[UUID]]:
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap")
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )
    sequence = dataset.get_sequences()[0]
    group_ids = [entry.sample_id for entry in sequence.get_samples()]
    return dataset, sequence, group_ids


def _cuboid(
    timestamp_ns: int, track_id: int, px: float = 4.0, parent_track_id: int | None = None
) -> CuboidLabel:
    return CuboidLabel(
        timestamp_ns=timestamp_ns,
        frame_id="odom",
        class_name="truck",
        track_id=track_id,
        parent_track_id=parent_track_id,
        interpolated=False,
        position=(px, 0.0, 0.5),
        rotation=(0.0, 0.0, 0.0, 1.0),
        size=(2.0, 1.0, 1.5),
    )
