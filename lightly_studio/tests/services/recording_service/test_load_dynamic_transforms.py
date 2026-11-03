"""Tests for load_dynamic_transforms."""

from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.resolvers import dynamic_transform_resolver
from lightly_studio.services.recording_service import load_dynamic_transforms
from lightly_studio.services.recording_service.load_dynamic_transforms import (
    DynamicTransformsByTime,
)
from tests.resolvers.static_transform_resolver.helpers import create_recording

# The window is 100 ms on each side of the capture time.
WINDOW_NS = 100_000_000


class TestDynamicTransformsByTime:
    def test_near(self) -> None:
        edges = DynamicTransformsByTime(
            edges=[
                _edge(timestamp_ns=1_200_000_000),
                _edge(timestamp_ns=1_000_000_000 - WINDOW_NS - 1),
                _edge(timestamp_ns=1_000_000_000 + WINDOW_NS),
                _edge(timestamp_ns=1_000_000_000 - WINDOW_NS),
            ]
        )

        result = edges.near(timestamp_ns=1_000_000_000)

        assert [edge.timestamp_ns for edge in result] == [
            1_000_000_000 - WINDOW_NS,
            1_000_000_000 + WINDOW_NS,
        ]


def test_load_dynamic_transforms_between(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    _store_edges(
        session=db_session,
        recording_id=recording_id,
        timestamps_ns=[1_000_000_000, 2_000_000_000, 3_000_000_000],
    )

    result = load_dynamic_transforms.load_dynamic_transforms_between(
        session=db_session,
        recording_id=recording_id,
        start_ns=1_000_000_000,
        end_ns=2_000_000_000,
    )

    assert result is not None
    assert sorted(edge.timestamp_ns for edge in result) == [1_000_000_000, 2_000_000_000]


def test_load_dynamic_transforms_between__no_edge_in_range(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)
    _store_edges(session=db_session, recording_id=recording_id, timestamps_ns=[3_000_000_000])

    result = load_dynamic_transforms.load_dynamic_transforms_between(
        session=db_session,
        recording_id=recording_id,
        start_ns=1_000_000_000,
        end_ns=2_000_000_000,
    )

    assert result == []


def test_load_dynamic_transforms_between__no_stored_edges(db_session: Session) -> None:
    recording_id = create_recording(session=db_session)

    result = load_dynamic_transforms.load_dynamic_transforms_between(
        session=db_session,
        recording_id=recording_id,
        start_ns=1_000_000_000,
        end_ns=2_000_000_000,
    )

    assert result is None


def _edge(timestamp_ns: int) -> StaticTransform:
    """Builds a `map` to `base_link` edge at a capture time."""
    return StaticTransform(
        parent_frame_id="map",
        child_frame_id="base_link",
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        timestamp_ns=timestamp_ns,
    )


def _store_edges(session: Session, recording_id: uuid.UUID, timestamps_ns: list[int]) -> None:
    """Stores one `map` to `base_link` edge per capture time."""
    dynamic_transform_resolver.create_many(
        session=session,
        rows=[
            DynamicTransformCreate(
                recording_id=recording_id,
                parent="map",
                child="base_link",
                timestamp_ns=timestamp_ns,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=0.0,
                ty=0.0,
                tz=0.0,
            )
            for timestamp_ns in timestamps_ns
        ],
    )
