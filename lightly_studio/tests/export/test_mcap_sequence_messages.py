from __future__ import annotations

import re
from pathlib import Path

import pytest

from lightly_studio.core.mcap import add_labels, add_mcaps
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.core.mcap.type_definitions import FrameTags, SceneUpdateLabels
from lightly_studio.database import db_manager
from lightly_studio.errors import ExportError
from lightly_studio.export import mcap_sequence_messages
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import (
    object_track_resolver,
)
from tests.core.mcap import helpers
from tests.core.mcap.test_add_mcaps import COMPONENTS, MAX_PAIRING_DIFF_NS
from tests.export import mcap_helpers


def test_build_sequence_messages__round_trip(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(tmp_path=tmp_path)
    first_ns, second_ns = helpers.LIDAR_LOG_TIMES_NS
    cuboids = (
        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=7),
        mcap_helpers.cuboid(
            timestamp_ns=first_ns, track_id=8, parent_track_id=7, interpolated=True
        ),
    )
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://round_trip_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=cuboids,
                    frame_tags=FrameTags(timestamp_ns=first_ns, tags=("night",), note=None),
                ),
            )
        ],
    )
    session = db_manager.persistent_session()
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=mcap_helpers.recording(session=session, sequence=sequence),
        sequence_id=sequence.sample_id,
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id="odom",
    )

    assert len(messages) == 2
    log_time_0, labels_0 = messages[0]
    # Track ids are object_track_numbers, so only the relations of the source ids remain.
    parent = next(cuboid for cuboid in labels_0.cuboids if not cuboid.interpolated)
    child = next(cuboid for cuboid in labels_0.cuboids if cuboid.interpolated)
    assert parent.track_id != child.track_id
    assert parent.parent_track_id is None
    assert child.parent_track_id == parent.track_id
    assert labels_0.frame_tags is not None
    assert labels_0.frame_tags.tags == ("night",)
    assert all(cuboid.timestamp_ns == first_ns for cuboid in labels_0.cuboids)
    assert log_time_0 == first_ns

    log_time_1, labels_1 = messages[1]
    assert labels_1.cuboids == ()
    assert labels_1.frame_tags is None
    assert log_time_1 == second_ns


def test_build_sequence_messages__cuboids_ordered_by_track_id(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(tmp_path=tmp_path)
    first_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    # The cuboids are stored in an order that differs from the track id order.
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ordered_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=9),
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=3),
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=5),
                    )
                ),
            )
        ],
    )
    session = db_manager.persistent_session()
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=mcap_helpers.recording(session=session, sequence=sequence),
        sequence_id=sequence.sample_id,
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id="odom",
    )

    track_ids = [cuboid.track_id for cuboid in messages[0][1].cuboids]
    assert len(set(track_ids)) == 3
    assert track_ids == sorted(track_ids)


def test_build_sequence_messages__other_annotation_set_is_ignored(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(tmp_path=tmp_path)
    first_ns, second_ns = helpers.LIDAR_LOG_TIMES_NS
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=7),)
                ),
            )
        ],
    )
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://predictions_labeled.mcap",
        messages=[
            (
                second_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=second_ns, track_id=9),)
                ),
            )
        ],
        annotation_source="predictions",
    )
    session = db_manager.persistent_session()
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=mcap_helpers.recording(session=session, sequence=sequence),
        sequence_id=sequence.sample_id,
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id="odom",
    )

    assert messages[1][1].cuboids == ()


def test_build_sequence_messages__transforms_to_target_frame(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path,
        base_link_poses=(
            (1_000_000_000, (10.0, 0.0, 0.0)),
            (1_300_000_000, (10.0, 0.0, 0.0)),
        ),
    )
    first_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://transform_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(
                            timestamp_ns=first_ns,
                            track_id=7,
                            frame_id=helpers.BASE_FRAME_ID,
                            px=4.0,
                            py=0.0,
                            pz=0.5,
                        ),
                    )
                ),
            )
        ],
    )
    session = db_manager.persistent_session()
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=mcap_helpers.recording(session=session, sequence=sequence),
        sequence_id=sequence.sample_id,
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id=helpers.WORLD_FRAME_ID,
    )

    cuboid = messages[0][1].cuboids[0]
    assert cuboid.frame_id == helpers.WORLD_FRAME_ID
    assert cuboid.position == pytest.approx((14.0, 0.0, 0.5))


def test_build_sequence_messages__untransformed_cuboid_fails(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # The recording has no /tf topic, so "odom" is not connected to any known frame.
    dataset, sequence, _ = mcap_helpers.index_recording(tmp_path=tmp_path)
    first_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://untransformed_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=7),)
                ),
            )
        ],
    )
    session = db_manager.persistent_session()
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    with pytest.raises(ExportError, match=re.escape(str(tmp_path / "recording.mcap"))):
        mcap_sequence_messages.build_sequence_messages(
            session=session,
            recording=mcap_helpers.recording(session=session, sequence=sequence),
            sequence_id=sequence.sample_id,
            annotation_collection_id=ground_truth.collection_id,
            target_frame_id=helpers.WORLD_FRAME_ID,
        )


def test_build_sequence_messages__untracked_cuboid_fails(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, group_ids = mcap_helpers.index_recording(tmp_path=tmp_path)
    session = db_manager.persistent_session()
    annotation_id = mcap_helpers.create_cuboid_annotation(
        session=session, dataset=dataset, parent_sample_id=group_ids[0], object_track_id=None
    )
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    with pytest.raises(ExportError, match=str(annotation_id)):
        mcap_sequence_messages.build_sequence_messages(
            session=session,
            recording=mcap_helpers.recording(session=session, sequence=sequence),
            sequence_id=sequence.sample_id,
            annotation_collection_id=ground_truth.collection_id,
            target_frame_id="odom",
        )


def test_build_sequence_messages__track_ids_are_object_track_numbers(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, group_ids = mcap_helpers.index_recording(tmp_path=tmp_path)
    session = db_manager.persistent_session()
    parent_track_id = object_track_resolver.create_many(
        session=session,
        tracks=[ObjectTrackCreate(object_track_number=41, dataset_id=dataset.dataset_id)],
    )[0]
    child_track_id = object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=42,
                dataset_id=dataset.dataset_id,
                source_track_id=7,
                parent_object_track_id=parent_track_id,
            )
        ],
    )[0]
    mcap_helpers.create_cuboid_annotation(
        session=session,
        dataset=dataset,
        parent_sample_id=group_ids[0],
        object_track_id=child_track_id,
    )
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=mcap_helpers.recording(session=session, sequence=sequence),
        sequence_id=sequence.sample_id,
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id="odom",
    )

    cuboid = messages[0][1].cuboids[0]
    assert cuboid.track_id == 42
    assert cuboid.parent_track_id == 41


def test_build_sequence_messages__log_time_falls_back_to_sweep_timestamp(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # Sync on the camera instead of the lidar, and shift the lidar capture timestamp so
    # it never equals the (camera-derived) sweep timestamp of any tick.
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap", lidar_stamp_offset_ns=-20_000_000)
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component="front",
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )
    sequence = dataset.get_sequences()[0]
    sweep_timestamp_ns = helpers.VIDEO_LOG_TIMES_NS[0]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://log_time_fallback_labeled.mcap",
        messages=[
            (
                sweep_timestamp_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=sweep_timestamp_ns, track_id=7),)
                ),
            )
        ],
    )
    session = db_manager.persistent_session()
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )

    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=mcap_helpers.recording(session=session, sequence=sequence),
        sequence_id=sequence.sample_id,
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id="odom",
    )

    log_time_ns, labels = messages[0]
    assert labels.cuboids[0].timestamp_ns == sweep_timestamp_ns
    assert log_time_ns == sweep_timestamp_ns
