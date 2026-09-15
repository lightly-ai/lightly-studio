"""Tests for reading static transform edges."""

from sqlmodel import Session

from lightly_studio.resolvers import static_transform_resolver
from tests.resolvers.static_transform_resolver.helpers import create_edge, create_recording


def test_get_all_by_recording_id(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    other_recording_id = create_recording(session=db_session)
    static_transform_resolver.create_many(
        session=db_session,
        rows=[
            create_edge(recording_id, parent="livox_front_left", child="Main_optical"),
            create_edge(recording_id, parent="livox_front_left", child="Left_optical"),
        ],
    )
    static_transform_resolver.create_many(
        session=db_session,
        rows=[create_edge(other_recording_id, parent="livox_front_left", child="Main_optical")],
    )

    rows = static_transform_resolver.get_all_by_recording_id(
        session=db_session, recording_id=recording_id
    )

    assert len(rows) == 2
    assert {row.recording_id for row in rows} == {recording_id}


def test_get_all_by_recording_id__no_rows(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    rows = static_transform_resolver.get_all_by_recording_id(
        session=db_session, recording_id=recording_id
    )

    assert rows == []
