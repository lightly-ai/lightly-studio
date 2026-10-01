"""Tests for get_tick_details."""

from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import annotation_resolver, group_resolver
from lightly_studio.services import recording_service
from tests.helpers_resolvers import create_annotation_label, create_mcap, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers


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
    assert set(result.camera_channels.keys()) == {"front"}
    assert result.camera_channels["front"].channel_id == 3
    assert result.camera_channels["front"].group_component_name == "front"
    assert result.camera_channels["front"].log_time_ns == "1000"
    assert result.camera_channels["front"].keyframe_log_time_ns == "1000"
    assert set(result.lidar_channels.keys()) == {"pcl_front"}
    assert result.lidar_channels["pcl_front"].channel_id == 7
    assert result.lidar_channels["pcl_front"].group_component_name == "pcl_front"
    assert result.lidar_channels["pcl_front"].log_time_ns == "1001"
    assert result.lidar_channels["pcl_front"].keyframe_log_time_ns is None
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
