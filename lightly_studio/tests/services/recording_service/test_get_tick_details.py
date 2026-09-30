"""Tests for get_tick_details."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import annotation_resolver, group_resolver
from lightly_studio.services import recording_service
from tests.core.mcap import helpers as mcap_helpers
from tests.helpers_resolvers import create_annotation_label, create_mcap, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture


def test_get_tick_details(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    camera = create_mcap(
        session=db_session,
        collection_id=fixture.slots["front"].collection_id,
        channel_id=3,
        log_time_ns=1_000,
        keyframe_log_time_ns=1_000,
    )
    lidar = create_mcap(
        session=db_session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=7,
        log_time_ns=1_001,
        keyframe_log_time_ns=None,
    )
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id, lidar.sample_id}],
    )
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=group_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=1_000,
        )
    )
    db_session.commit()

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
    )

    assert result is not None
    assert result.recording_id == fixture.recording_id
    assert result.seq_number == 0
    assert result.timestamp_ns == 1_000
    assert set(result.channels.keys()) == {"front", "pcl_front"}
    assert result.channels["front"].channel_id == 3
    assert result.channels["front"].group_component_name == "front"
    assert result.channels["front"].log_time_ns == "1000"
    assert result.channels["front"].keyframe_log_time_ns == "1000"
    assert result.channels["pcl_front"].channel_id == 7
    assert result.channels["pcl_front"].group_component_name == "pcl_front"
    assert result.channels["pcl_front"].log_time_ns == "1001"
    assert result.channels["pcl_front"].keyframe_log_time_ns is None
    assert result.annotations == []


def test_get_tick_details__annotations(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set(), set()],
    )
    for seq_number, group_id in enumerate(group_ids):
        db_session.add(
            SampleSequenceLinkTable(
                sample_id=group_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
                timestamp_ns=1_000 + seq_number,
            )
        )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=fixture.group_collection.collection_id,
        label_name="truck",
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                px=1.0,
            ),
            cuboid_create(
                parent_sample_id=group_ids[1],
                annotation_label_id=label.annotation_label_id,
                px=5.0,
            ),
        ],
        collection_name="ground_truth",
    )
    db_session.commit()

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
    )

    assert result is not None
    assert len(result.annotations) == 1
    annotation = result.annotations[0]
    assert annotation.parent_sample_id == group_ids[0]
    assert annotation.annotation_type == AnnotationType.CUBOID_3D
    assert annotation.annotation_label.annotation_label_name == "truck"
    assert annotation.cuboid_3d_details is not None
    assert annotation.cuboid_3d_details.px == pytest.approx(1.0)


def test_get_tick_details__target_frame_id(db_session: Session, tmp_path: Path) -> None:
    path = mcap_helpers.write_mcap_with_dynamic_transforms(tmp_path / "with_tf.mcap")
    fixture = helpers.create_mcap_sequence(session=db_session, uri=str(path))
    _add_tick_with_cuboid(session=db_session, fixture=fixture, timestamp_ns=1_150_000_000)

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
        target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
    )

    assert result is not None
    cuboid = result.annotations[0].cuboid_3d_details
    assert cuboid is not None
    assert cuboid.frame_id == mcap_helpers.LIDAR_FRAME_ID
    # At 1.2 s the base is 20 m ahead in the world and turned by 90 degrees, and the
    # lidar is mounted at (0, 1, 2) in the base frame. See `test_get_transform_at`.
    assert (cuboid.px, cuboid.py, cuboid.pz) == pytest.approx((0.0, 19.0, -1.5))
    assert (cuboid.qx, cuboid.qy, cuboid.qz, cuboid.qw) == pytest.approx(
        (0.0, 0.0, -0.7071067811865476, 0.7071067811865476)
    )
    assert (cuboid.sx, cuboid.sy, cuboid.sz) == pytest.approx((2.0, 1.0, 1.5))


def test_get_tick_details__target_frame_id_of_cuboid(db_session: Session) -> None:
    # The recording URI does not exist, so the test fails if the recording is read.
    fixture = helpers.create_mcap_sequence(session=db_session, uri="/missing/recording.mcap")
    _add_tick_with_cuboid(session=db_session, fixture=fixture, timestamp_ns=1_000)

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=0,
        target_frame_id="odom",
    )

    assert result is not None
    cuboid = result.annotations[0].cuboid_3d_details
    assert cuboid is not None
    assert cuboid.frame_id == "odom"
    assert (cuboid.px, cuboid.py, cuboid.pz) == pytest.approx((0.0, 0.0, 0.5))


def test_get_tick_details__target_frame_id_without_timestamp(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    _add_tick_with_cuboid(session=db_session, fixture=fixture, timestamp_ns=None)

    with pytest.raises(McapAccessError, match="The tick has no timestamp"):
        recording_service.get_tick_details(
            session=db_session,
            dataset_id=fixture.sequence_collection.dataset_id,
            sequence_id=fixture.sample_id,
            seq_number=0,
            target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
        )


def test_get_tick_details__unknown_sequence(db_session: Session) -> None:
    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=uuid.uuid4(),
        sequence_id=uuid.uuid4(),
        seq_number=0,
    )

    assert result is None


def test_get_tick_details__wrong_dataset(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=uuid.uuid4(),
        sequence_id=fixture.sample_id,
        seq_number=0,
    )

    assert result is None


def test_get_tick_details__unknown_seq_number(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_tick_details(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        seq_number=99,
    )

    assert result is None


def _add_tick_with_cuboid(
    session: Session, fixture: McapSequenceFixture, timestamp_ns: int | None
) -> None:
    """Index one tick with a cuboid at (0, 0, 0.5) in the `odom` frame."""
    group_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set()],
    )
    session.add(
        SampleSequenceLinkTable(
            sample_id=group_ids[0],
            sequence_sample_id=fixture.sample_id,
            seq_number=0,
            timestamp_ns=timestamp_ns,
        )
    )
    label = create_annotation_label(
        session=session,
        root_collection_id=fixture.group_collection.collection_id,
        label_name="truck",
    )
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[0], annotation_label_id=label.annotation_label_id, px=0.0
            )
        ],
        collection_name="ground_truth",
    )
    session.commit()
