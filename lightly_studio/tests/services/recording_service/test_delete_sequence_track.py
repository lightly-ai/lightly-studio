from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from lightly_studio.services import recording_service
from tests.services.recording_service.test_extend_sequence_track import (
    _create_track,
    _Setup,
    _track_annotations,
)


def test_delete_sequence_track(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=5, covered=[1, 2, 3])
    annotation_ids = [a.annotation_id for a in _track_annotations(session=db_session, setup=setup)]

    deleted = _delete(session=db_session, setup=setup)

    assert deleted == 3
    for annotation_id in annotation_ids:
        assert (
            annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id) is None
        )
    tracks = recording_service.get_sequence_tracks(
        session=db_session,
        dataset_id=setup.fixture.sequence_collection.dataset_id,
        sequence_id=setup.fixture.sample_id,
    )
    assert tracks is not None
    assert tracks.tracks == []
    remaining = object_track_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=setup.fixture.sequence_collection.dataset_id
    )
    assert setup.track_id not in [track.object_track_id for track in remaining]


def test_delete_sequence_track__keeps_other_tracks(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[0, 1])
    other = _create_track(session=db_session, tick_count=3, covered=[0, 1])

    _delete(session=db_session, setup=setup)

    assert len(_track_annotations(session=db_session, setup=other)) == 2


def test_delete_sequence_track__keeps_parent_with_child_track(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[0, 1, 2])
    child_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=2,
                dataset_id=setup.fixture.sequence_collection.dataset_id,
                parent_object_track_id=setup.track_id,
            )
        ],
    )[0]
    child_annotation = _track_annotations(session=db_session, setup=setup)[2]
    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=child_annotation.annotation_id,
        object_track_id=child_id,
    )

    assert _delete(session=db_session, setup=setup) == 2
    assert (
        annotation_resolver.get_all_by_object_track_id(
            session=db_session, object_track_id=setup.track_id
        )
        == []
    )

    remaining = object_track_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=setup.fixture.sequence_collection.dataset_id
    )
    assert {track.object_track_id for track in remaining} == {setup.track_id, child_id}
    child = next(track for track in remaining if track.object_track_id == child_id)
    assert child.parent_object_track_id == setup.track_id
    assert (
        annotation_resolver.get_by_id(
            session=db_session, annotation_id=child_annotation.annotation_id
        )
        is not None
    )


def test_delete_sequence_track__retry_is_rejected(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[1])
    _delete(session=db_session, setup=setup)

    with pytest.raises(ValueError, match="no annotations from this source"):
        _delete(session=db_session, setup=setup)


def test_delete_sequence_track__unknown_sequence(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[1])

    result = recording_service.delete_sequence_track(
        session=db_session,
        dataset_id=setup.fixture.sequence_collection.dataset_id,
        sequence_id=setup.fixture.group_collection.collection_id,
        track_id=setup.track_id,
        annotation_source_id=setup.source_id,
    )

    assert result is None


def _delete(session: Session, setup: _Setup) -> int | None:
    return recording_service.delete_sequence_track(
        session=session,
        dataset_id=setup.fixture.sequence_collection.dataset_id,
        sequence_id=setup.fixture.sample_id,
        track_id=setup.track_id,
        annotation_source_id=setup.source_id,
    )
