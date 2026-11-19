"""Tests for reading the dynamic transform edges closest to a range of capture times."""

import uuid

from sqlmodel import Session

from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.resolvers import dynamic_transform_resolver
from tests.resolvers.static_transform_resolver.helpers import create_recording


def test_get_closest_outside(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    dynamic_transform_resolver.create_many(
        session=db_session,
        rows=[
            _edge(recording_id=recording_id, child="base_link", timestamp_ns=timestamp_ns)
            for timestamp_ns in (100, 200, 500, 800, 900)
        ]
        + [_edge(recording_id=recording_id, child="lidar", timestamp_ns=50)],
    )

    rows = dynamic_transform_resolver.get_closest_outside(
        session=db_session, recording_id=recording_id, start_ns=300, end_ns=700
    )

    assert sorted((row.child, row.timestamp_ns) for row in rows) == [
        ("base_link", 200),
        ("base_link", 800),
        ("lidar", 50),
    ]


def test_get_closest_outside__ignores_other_recordings(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    other_recording_id = create_recording(session=db_session)
    dynamic_transform_resolver.create_many(
        session=db_session,
        rows=[_edge(recording_id=other_recording_id, child="base_link", timestamp_ns=100)],
    )

    rows = dynamic_transform_resolver.get_closest_outside(
        session=db_session, recording_id=recording_id, start_ns=300, end_ns=700
    )

    assert rows == []


def _edge(recording_id: uuid.UUID, child: str, timestamp_ns: int) -> DynamicTransformCreate:
    return DynamicTransformCreate(
        recording_id=recording_id,
        parent="map",
        child=child,
        timestamp_ns=timestamp_ns,
        qx=0.0,
        qy=0.0,
        qz=0.0,
        qw=1.0,
        tx=0.0,
        ty=0.0,
        tz=0.0,
    )
