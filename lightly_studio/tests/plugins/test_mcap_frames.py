"""Tests for the MCAP frame access of plugins."""

from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.plugins import mcap_frames
from lightly_studio.plugins.operator_context import ExecutionContext
from lightly_studio.resolvers import annotation_resolver, sequence_resolver, tag_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import create_annotation_label, create_tag, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers

URI = "/data/rosbag2_2026_05_01.mcap"


def test_get_sequence_ids(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    sequence_ids = mcap_frames.get_sequence_ids(
        session=db_session,
        context=ExecutionContext(collection_id=fixture.sequence_collection.collection_id),
    )

    assert sequence_ids == [fixture.sample_id]


@pytest.mark.parametrize("is_selected", [True, False])
def test_get_sequence_ids__sample_filter(db_session: Session, is_selected: bool) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    selected_id = fixture.sample_id if is_selected else uuid.uuid4()

    sequence_ids = mcap_frames.get_sequence_ids(
        session=db_session,
        context=ExecutionContext(
            collection_id=fixture.sequence_collection.collection_id,
            context_filter=SampleFilter(sample_ids=[selected_id]),
        ),
    )

    assert sequence_ids == ([fixture.sample_id] if is_selected else [])


def test_get_sequence_ids__not_a_sequence_collection(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    with pytest.raises(ValueError, match="MCAP sequence collection"):
        mcap_frames.get_sequence_ids(
            session=db_session,
            context=ExecutionContext(collection_id=fixture.group_collection.collection_id),
        )


def test_iter_frames(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session, uri=URI)
    # The helper captures the lidar 1 ns after the camera.
    helpers.add_mcap_ticks_to_sequence(
        session=db_session, fixture=fixture, ticks=[(100, 100), (200, 100)]
    )

    frames = list(mcap_frames.iter_frames(session=db_session, sequence_ids=[fixture.sample_id]))

    assert [(frame.seq_number, frame.timestamp_ns) for frame in frames] == [(0, 100), (1, 200)]
    frame = frames[1]
    assert frame.sequence_id == fixture.sample_id
    assert frame.recording_id == fixture.recording_id
    assert frame.recording_uri == URI
    assert frame.capture_timestamps_ns == {"front": 200, "pcl_front": 201}
    assert frame.annotations == []
    assert frame.tags == []


def test_iter_frames__annotations_and_tags(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    helpers.add_mcap_ticks_to_sequence(
        session=db_session, fixture=fixture, ticks=[(100, 100), (200, 100)]
    )
    links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=fixture.sample_id
    )
    group_collection_id = fixture.group_collection.collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=group_collection_id, label_name="truck"
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=group_collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=links[1].sample_id,
                annotation_label_id=label.annotation_label_id,
                px=12.5,
            )
        ],
        collection_name="ground_truth",
    )
    tag = create_tag(session=db_session, collection_id=group_collection_id, tag_name="skip")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[links[0].sample_id]
    )

    frames = list(mcap_frames.iter_frames(session=db_session, sequence_ids=[fixture.sample_id]))

    assert frames[0].annotations == []
    assert frames[0].tags == ["skip"]
    cuboid = frames[1].annotations[0].cuboid_3d_details
    assert cuboid is not None
    assert cuboid.px == pytest.approx(12.5)
    assert frames[1].tags == []


def test_iter_frames__not_an_mcap_sequence(db_session: Session) -> None:
    with pytest.raises(ValueError, match="is not an MCAP sequence"):
        mcap_frames.iter_frames(session=db_session, sequence_ids=[uuid.uuid4()])
