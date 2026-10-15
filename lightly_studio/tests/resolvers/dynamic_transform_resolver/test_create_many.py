"""Tests for creating and reading dynamic transform edges."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.resolvers import dynamic_transform_resolver
from tests.resolvers.static_transform_resolver.helpers import create_recording


def test_create_many__stores_repeated_edges(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    ids = dynamic_transform_resolver.create_many(
        session=db_session,
        rows=[
            _edge(recording_id=recording_id, timestamp_ns=0),
            _edge(recording_id=recording_id, timestamp_ns=200_000_000),
        ],
    )

    assert len(ids) == 2
    rows = dynamic_transform_resolver.get_near(
        session=db_session,
        recording_id=recording_id,
        start_ns=0,
        end_ns=200_000_000,
    )
    assert {row.dynamic_transform_id for row in rows} == set(ids)
    assert {row.timestamp_ns for row in rows} == {0, 200_000_000}


def test_get_near__keeps_the_window(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    dynamic_transform_resolver.create_many(
        session=db_session,
        rows=[
            _edge(recording_id=recording_id, timestamp_ns=0),
            _edge(recording_id=recording_id, timestamp_ns=200_000_000),
        ],
    )

    rows = dynamic_transform_resolver.get_near(
        session=db_session,
        recording_id=recording_id,
        start_ns=0,
        end_ns=100_000_000,
    )

    assert [row.timestamp_ns for row in rows] == [0]


def test_has_any(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    assert not dynamic_transform_resolver.has_any(session=db_session, recording_id=recording_id)

    dynamic_transform_resolver.create_many(
        session=db_session, rows=[_edge(recording_id=recording_id, timestamp_ns=0)]
    )

    assert dynamic_transform_resolver.has_any(session=db_session, recording_id=recording_id)


def test_create_many__empty_rows(db_session: Session) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        dynamic_transform_resolver.create_many(session=db_session, rows=[])


def test_create_many__empty_frame_id(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    with pytest.raises(ValueError, match="parent"):
        dynamic_transform_resolver.create_many(
            session=db_session, rows=[_edge(recording_id=recording_id, timestamp_ns=0, parent=" ")]
        )


def _edge(
    recording_id: uuid.UUID,
    timestamp_ns: int,
    parent: str = "map",
    child: str = "base_link",
) -> DynamicTransformCreate:
    return DynamicTransformCreate(
        recording_id=recording_id,
        parent=parent,
        child=child,
        timestamp_ns=timestamp_ns,
        qx=0.0,
        qy=0.0,
        qz=0.0,
        qw=1.0,
        tx=1.0,
        ty=0.0,
        tz=0.0,
    )
