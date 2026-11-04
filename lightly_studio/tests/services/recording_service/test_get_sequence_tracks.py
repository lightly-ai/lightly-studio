from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import annotation_resolver, group_resolver, object_track_resolver
from lightly_studio.services import recording_service
from tests.helpers_resolvers import create_annotation_label, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture


def test_get_sequence_tracks(db_session: Session) -> None:
    fixture = _create_tracked_sequence(session=db_session, timestamps_ns=[1_000, 1_001])

    result = recording_service.get_sequence_tracks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )

    assert result is not None
    assert len(result.tracks) == 1
    track = result.tracks[0]
    assert track.object_track_number == 7
    assert track.annotation_label_name == "truck"
    assert [annotation.seq_number for annotation in track.annotations] == [0, 1]
    assert [annotation.frame_id for annotation in track.annotations] == ["odom", "odom"]


def test_get_sequence_tracks__target_frame_of_cuboids(db_session: Session) -> None:
    # The cuboids are already in "odom", so no transform is needed.
    fixture = _create_tracked_sequence(session=db_session, timestamps_ns=[None, 1_001])

    result = recording_service.get_sequence_tracks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        target_frame_id="odom",
    )

    assert result is not None
    assert [annotation.seq_number for annotation in result.tracks[0].annotations] == [0, 1]


def test_get_sequence_tracks__hides_ticks_without_timestamp(db_session: Session) -> None:
    # Tick 0 has no timestamp, so its "odom" cuboid cannot be mapped to "base_link".
    fixture = _create_tracked_sequence(session=db_session, timestamps_ns=[None])

    result = recording_service.get_sequence_tracks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        target_frame_id="base_link",
    )

    assert result is not None
    assert len(result.tracks) == 1
    assert result.tracks[0].annotations == []


def test_get_sequence_tracks__unknown_sequence(db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    result = recording_service.get_sequence_tracks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.group_collection.collection_id,
    )

    assert result is None


def _create_tracked_sequence(
    session: Session, timestamps_ns: list[int | None]
) -> McapSequenceFixture:
    """Creates a sequence with one tracked "odom" cuboid per tick."""
    fixture = helpers.create_mcap_sequence(session=session)
    group_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set() for _ in timestamps_ns],
    )
    for seq_number, (group_id, timestamp_ns) in enumerate(zip(group_ids, timestamps_ns)):
        session.add(
            SampleSequenceLinkTable(
                sample_id=group_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
                timestamp_ns=timestamp_ns,
            )
        )
    label = create_annotation_label(
        session=session,
        root_collection_id=fixture.group_collection.collection_id,
        label_name="truck",
    )
    track_id = object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=7, dataset_id=fixture.sequence_collection.dataset_id
            )
        ],
    )[0]
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            )
            for group_id in group_ids
        ],
        collection_name="ground_truth",
    )
    session.commit()
    return fixture
