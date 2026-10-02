"""Tests for the checks of the frames a recording's scene can be shown in."""

import pytest

from lightly_studio.core.mcap import reference_frames
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.type_definitions import StaticTransform


def _edge(parent_frame_id: str, child_frame_id: str) -> StaticTransform:
    return StaticTransform(
        parent_frame_id=parent_frame_id,
        child_frame_id=child_frame_id,
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        timestamp_ns=0,
    )


def test_known_reference_frame_ids__keeps_the_given_order() -> None:
    frame_ids = reference_frames.known_reference_frame_ids(
        frame_ids=["CABIN", "map"],
        static_transforms=[_edge(parent_frame_id="CABIN", child_frame_id="lidar")],
        dynamic_edges=[("map", "CABIN")],
    )

    assert frame_ids == ["CABIN", "map"]


def test_known_reference_frame_ids__missing() -> None:
    with pytest.raises(McapAccessError, match="map"):
        reference_frames.known_reference_frame_ids(
            frame_ids=["map"],
            static_transforms=[_edge(parent_frame_id="base", child_frame_id="lidar")],
            dynamic_edges=[],
        )


def test_check_reference_frame_ids__empty_id() -> None:
    with pytest.raises(ValueError, match="empty"):
        reference_frames.check_reference_frame_ids(frame_ids=["map", ""])


def test_check_reference_frame_ids__repeated() -> None:
    with pytest.raises(ValueError, match="map"):
        reference_frames.check_reference_frame_ids(frame_ids=["map", "map"])
