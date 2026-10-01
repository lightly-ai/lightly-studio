"""Tests for creating static transform edges."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.resolvers import static_transform_resolver
from tests.resolvers.static_transform_resolver.helpers import create_edge, create_recording


def test_create_many(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    ids = static_transform_resolver.create_many(
        session=db_session,
        rows=[
            create_edge(recording_id, parent="livox_front_left", child="Main_optical"),
            create_edge(recording_id, parent="livox_front_left", child="Left_optical"),
        ],
    )

    assert len(ids) == 2
    rows = static_transform_resolver.get_all_by_recording_id(
        session=db_session, recording_id=recording_id
    )
    assert {row.static_transform_id for row in rows} == set(ids)
    assert {row.child for row in rows} == {"Main_optical", "Left_optical"}
    main_row = next(row for row in rows if row.child == "Main_optical")
    assert main_row.parent == "livox_front_left"
    assert (main_row.qx, main_row.qy, main_row.qz, main_row.qw) == pytest.approx(
        (0.0, 0.0, 0.0, 1.0)
    )
    assert (main_row.tx, main_row.ty, main_row.tz) == pytest.approx((0.1, 0.2, 0.3))


def test_create_many__unique_edge(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    static_transform_resolver.create_many(session=db_session, rows=[create_edge(recording_id)])

    with pytest.raises(IntegrityError):
        static_transform_resolver.create_many(session=db_session, rows=[create_edge(recording_id)])
    db_session.rollback()


def test_create_many__missing_recording(db_session: Session) -> None:
    with pytest.raises(ValueError, match=r"Recording with id .* not found"):
        static_transform_resolver.create_many(session=db_session, rows=[create_edge(uuid.uuid4())])


def test_create_many__empty_rows(db_session: Session) -> None:
    with pytest.raises(ValueError, match="rows must be non-empty"):
        static_transform_resolver.create_many(session=db_session, rows=[])


def test_create_many__empty_parent(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    with pytest.raises(ValueError, match="parent must be non-empty"):
        static_transform_resolver.create_many(
            session=db_session, rows=[create_edge(recording_id, parent="  ")]
        )


def test_create_many__empty_child(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    with pytest.raises(ValueError, match="child must be non-empty"):
        static_transform_resolver.create_many(
            session=db_session, rows=[create_edge(recording_id, child="  ")]
        )
