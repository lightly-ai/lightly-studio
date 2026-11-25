from __future__ import annotations

from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    annotation_resolver,
    group_resolver,
    object_track_resolver,
)
from lightly_studio.services import recording_service
from tests.helpers_resolvers import create_annotation_label, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture


def test_start_sequence_track(db_session: Session) -> None:
    fixture, annotation_ids = _create_sequence_with_cuboids(session=db_session)
    # The dataset already has a track 7, so the new one is numbered 8.
    object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=7, dataset_id=fixture.sequence_collection.dataset_id
            )
        ],
    )

    track = recording_service.start_sequence_track(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        annotation_id=annotation_ids[0],
    )

    assert track is not None
    assert track.object_track_number == 8
    annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_ids[0])
    assert annotation is not None
    assert annotation.object_track_id == track.object_track_id
    tracks = recording_service.get_sequence_tracks(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )
    assert tracks is not None
    assert [
        (view.object_track_number, [a.seq_number for a in view.annotations])
        for view in tracks.tracks
    ] == [(8, [0])]


def test_start_sequence_track__first_track_of_dataset_is_number_one(db_session: Session) -> None:
    fixture, annotation_ids = _create_sequence_with_cuboids(session=db_session)

    track = recording_service.start_sequence_track(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
        annotation_id=annotation_ids[0],
    )

    assert track is not None
    assert track.object_track_number == 1


def test_start_sequence_track__rejects_tracked_annotation(db_session: Session) -> None:
    fixture, annotation_ids = _create_sequence_with_cuboids(session=db_session)
    dataset_id = fixture.sequence_collection.dataset_id
    recording_service.start_sequence_track(
        session=db_session,
        dataset_id=dataset_id,
        sequence_id=fixture.sample_id,
        annotation_id=annotation_ids[0],
    )

    with pytest.raises(ValueError, match="already belongs to a track"):
        recording_service.start_sequence_track(
            session=db_session,
            dataset_id=dataset_id,
            sequence_id=fixture.sample_id,
            annotation_id=annotation_ids[0],
        )

    tracks = object_track_resolver.get_all_by_dataset_id(session=db_session, dataset_id=dataset_id)
    assert len(tracks) == 1


def test_start_sequence_track__rejects_annotation_of_other_sequence(db_session: Session) -> None:
    fixture, _ = _create_sequence_with_cuboids(session=db_session)
    _, other_annotation_ids = _create_sequence_with_cuboids(session=db_session)

    with pytest.raises(ValueError, match="is not on a tick of sequence"):
        recording_service.start_sequence_track(
            session=db_session,
            dataset_id=fixture.sequence_collection.dataset_id,
            sequence_id=fixture.sample_id,
            annotation_id=other_annotation_ids[0],
        )


def test_start_sequence_track__unknown_sequence(db_session: Session) -> None:
    fixture, annotation_ids = _create_sequence_with_cuboids(session=db_session)

    result = recording_service.start_sequence_track(
        session=db_session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.group_collection.collection_id,
        annotation_id=annotation_ids[0],
    )

    assert result is None


def test_start_sequence_track__failed_attach_leaves_no_track(
    db_session: Session, mocker: MockerFixture
) -> None:
    fixture, annotation_ids = _create_sequence_with_cuboids(session=db_session)
    dataset_id = fixture.sequence_collection.dataset_id
    mocker.patch.object(
        object_track_resolver,
        "add_annotation_to_object_track",
        side_effect=ValueError("cannot attach"),
    )

    with pytest.raises(ValueError, match="cannot attach"):
        recording_service.start_sequence_track(
            session=db_session,
            dataset_id=dataset_id,
            sequence_id=fixture.sample_id,
            annotation_id=annotation_ids[0],
        )

    tracks = object_track_resolver.get_all_by_dataset_id(session=db_session, dataset_id=dataset_id)
    assert tracks == []


def _create_sequence_with_cuboids(session: Session) -> tuple[McapSequenceFixture, list[UUID]]:
    """Creates a two tick sequence with one untracked cuboid per tick."""
    fixture = helpers.create_mcap_sequence(session=session)
    group_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set(), set()],
    )
    for seq_number, group_id in enumerate(group_ids):
        session.add(
            SampleSequenceLinkTable(
                sample_id=group_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
                timestamp_ns=1_000 + seq_number,
            )
        )
    label = create_annotation_label(
        session=session,
        root_collection_id=fixture.group_collection.collection_id,
        label_name="truck",
    )
    annotation_ids = annotation_resolver.create_many(
        session=session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(parent_sample_id=group_id, annotation_label_id=label.annotation_label_id)
            for group_id in group_ids
        ],
        collection_name="ground_truth",
    )
    session.commit()
    return fixture, annotation_ids
