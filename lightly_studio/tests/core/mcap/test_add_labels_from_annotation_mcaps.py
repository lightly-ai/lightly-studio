from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from lightly_studio.core.mcap import add_mcaps, annotation_mcap
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.mcap_dataset import McapDataset
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
SCENE_UPDATE_SCHEMA = "foxglove_msgs/msg/SceneUpdate"
SCENE_UPDATE_TOPIC = "/scene_update"


def test_add_labels_from_annotation_mcaps(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, group_ids = _index_recording(tmp_path=tmp_path)
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    _write_annotation_mcap(
        source_path=tmp_path / "recording.mcap",
        messages=[
            (
                timestamp_ns + 10_000_000,
                {"entities": [_cuboid_entity(timestamp_ns=timestamp_ns, track_id=7, px=4.0)]},
            )
        ],
    )

    dataset.add_labels_from_annotation_mcaps(topic=SCENE_UPDATE_TOPIC)

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert len(annotations) == 1
    assert annotations[0].parent_sample_id == group_ids[0]
    assert annotations[0].cuboid_3d_details is not None
    assert annotations[0].cuboid_3d_details.px == 4.0
    assert annotations[0].object_track_id is not None
    track = object_track_resolver.get_by_id(
        session=db_manager.persistent_session(),
        object_track_id=annotations[0].object_track_id,
    )
    assert track is not None
    assert track.source_track_id == 7


def test_add_labels_from_annotation_mcaps__path(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, group_ids = _index_recording(tmp_path=tmp_path)
    labels_path = tmp_path / "labels"
    labels_path.mkdir()
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    _write_annotation_mcap(
        source_path=labels_path / "recording.mcap",
        messages=[
            (timestamp_ns, {"entities": [_cuboid_entity(timestamp_ns=timestamp_ns, track_id=1)]})
        ],
    )

    dataset.add_labels_from_annotation_mcaps(topic=SCENE_UPDATE_TOPIC, path=labels_path)

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert len(annotations) == 1
    assert annotations[0].parent_sample_id == group_ids[0]


def test_add_labels_from_annotation_mcaps__missing_annotation_mcap(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, group_ids = _index_recording(tmp_path=tmp_path)

    dataset.add_labels_from_annotation_mcaps(topic=SCENE_UPDATE_TOPIC)

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert annotations == []


def test_add_labels_from_annotation_mcaps__broken_annotation_mcap(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, group_ids = _index_recording(tmp_path=tmp_path)
    (tmp_path / "recording_labeled.mcap").write_bytes(b"not an mcap file")

    dataset.add_labels_from_annotation_mcaps(topic=SCENE_UPDATE_TOPIC)

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert annotations == []


def test_add_mcaps_from_path__add_labels(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    helpers.write_mcap(tmp_path / "recording.mcap")
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    _write_annotation_mcap(
        source_path=tmp_path / "recording.mcap",
        messages=[
            (timestamp_ns, {"entities": [_cuboid_entity(timestamp_ns=timestamp_ns, track_id=1)]})
        ],
    )
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    dataset.add_mcaps_from_path(
        path=tmp_path,
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
        add_labels=True,
        topic=SCENE_UPDATE_TOPIC,
    )

    group_ids = [entry.sample_id for entry in dataset.get_sequences()[0].get_samples()]
    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert len(annotations) == 1


def test_add_labels_from_annotation_mcaps__restrict_to_sequence_ids(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, group_ids = _index_recording(tmp_path=tmp_path)
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    _write_annotation_mcap(
        source_path=tmp_path / "recording.mcap",
        messages=[
            (timestamp_ns, {"entities": [_cuboid_entity(timestamp_ns=timestamp_ns, track_id=1)]})
        ],
    )

    dataset.add_labels_from_annotation_mcaps(
        topic=SCENE_UPDATE_TOPIC, restrict_to_sequence_ids=set()
    )

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert annotations == []


def test_add_mcaps_from_path__add_labels_twice(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    helpers.write_mcap(tmp_path / "recording.mcap")
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    _write_annotation_mcap(
        source_path=tmp_path / "recording.mcap",
        messages=[
            (timestamp_ns, {"entities": [_cuboid_entity(timestamp_ns=timestamp_ns, track_id=1)]})
        ],
    )
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    for _ in range(2):
        dataset.add_mcaps_from_path(
            path=tmp_path,
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
            max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
            add_labels=True,
            topic=SCENE_UPDATE_TOPIC,
        )

    group_ids = [entry.sample_id for entry in dataset.get_sequences()[0].get_samples()]
    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert len(annotations) == 1


def test_add_mcaps_from_path__custom_annotation_mcap_options(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    helpers.write_mcap(tmp_path / "recording.mcap")
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    _write_annotation_mcap(
        source_path=tmp_path / "recording.mcap",
        suffix="_gt",
        messages=[
            (timestamp_ns, {"entities": [_cuboid_entity(timestamp_ns=timestamp_ns, track_id=1)]})
        ],
    )
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    dataset.add_mcaps_from_path(
        path=tmp_path,
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
        add_labels=True,
        topic=SCENE_UPDATE_TOPIC,
        suffix="_gt",
        annotation_source="ground_truth_custom",
    )

    assert len(dataset.get_sequences()) == 1
    group_ids = [entry.sample_id for entry in dataset.get_sequences()[0].get_samples()]
    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_manager.persistent_session(),
        parent_sample_ids=group_ids,
        annotation_types=[AnnotationType.CUBOID_3D],
    )
    assert len(annotations) == 1
    assert annotations[0].sample.collection.name == "ground_truth_custom"


def _index_recording(tmp_path: Path) -> tuple[McapDataset, list[UUID]]:
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap")
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )
    group_ids = [entry.sample_id for entry in dataset.get_sequences()[0].get_samples()]
    return dataset, group_ids


def _write_annotation_mcap(
    source_path: Path,
    messages: list[tuple[int, dict[str, Any]]],
    suffix: str = annotation_mcap.DEFAULT_ANNOTATION_MCAP_SUFFIX,
) -> Path:
    annotation_mcap_path = Path(
        annotation_mcap.annotation_mcap_uri(recording_uri=str(source_path), suffix=suffix)
    )
    return helpers.write_json_mcap(
        path=annotation_mcap_path,
        topic=SCENE_UPDATE_TOPIC,
        schema_name=SCENE_UPDATE_SCHEMA,
        messages=messages,
    )


def _cuboid_entity(
    timestamp_ns: int,
    track_id: int,
    class_name: str = "truck",
    parent_track_id: int | None = None,
    px: float = 1.0,
) -> dict[str, Any]:
    metadata = [
        {"key": "class", "value": class_name},
        {"key": "track_id", "value": str(track_id)},
    ]
    if parent_track_id is not None:
        metadata.append({"key": "parent_track_id", "value": str(parent_track_id)})
    return {
        "id": f"{class_name}_{track_id}",
        "timestamp": _time(timestamp_ns),
        "frame_id": "odom",
        "metadata": metadata,
        "cubes": [
            {
                "pose": {
                    "position": {"x": px, "y": 0.0, "z": 0.5},
                    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                },
                "size": {"x": 2.0, "y": 1.0, "z": 1.5},
            }
        ],
    }


def _time(timestamp_ns: int) -> dict[str, int]:
    return {"sec": timestamp_ns // 1_000_000_000, "nsec": timestamp_ns % 1_000_000_000}
