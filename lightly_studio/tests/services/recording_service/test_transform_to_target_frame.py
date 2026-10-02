"""Tests for transform_to_target_frame."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from lightly_studio.core.mcap.errors import TransformNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.services.recording_service import transform_to_target_frame
from tests.core.mcap import helpers


def test_transform_to_target_frame(tmp_path: Path) -> None:
    mcap_path = helpers.write_mcap(
        path=tmp_path / "with_tf.mcap",
        base_link_poses=[
            (1_000_000_000, (10.0, 0.0, 0.0)),
            (1_050_000_000, (20.0, 0.0, 0.0)),
        ],
    )
    # The lidar sits at (0, 1, 2) m in the base frame, without rotation.
    static_transforms = [
        StaticTransform(
            parent_frame_id=helpers.BASE_FRAME_ID,
            child_frame_id=helpers.LIDAR_FRAME_ID,
            translation=(0.0, 1.0, 2.0),
            rotation=(0.0, 0.0, 0.0, 1.0),
            timestamp_ns=0,
        )
    ]

    with McapFileReader(mcap_path) as reader:
        matrix = transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=helpers.LIDAR_FRAME_ID,
            target_frame_id=helpers.WORLD_FRAME_ID,
            timestamp_ns=1_050_000_000,
            static_transforms=static_transforms,
        )

    # The base frame is at x = 20 m in the map at 1.05 s.
    assert matrix is not None
    assert np.allclose(matrix[:3, 3], (20.0, 1.0, 2.0))
    assert np.allclose(matrix[:3, :3], np.eye(3))


@pytest.mark.parametrize("target_frame_id", [None, helpers.LIDAR_FRAME_ID])
def test_transform_to_target_frame__source_frame_kept(
    tmp_path: Path, target_frame_id: str | None
) -> None:
    mcap_path = helpers.write_mcap(path=tmp_path / "recording.mcap")

    with McapFileReader(mcap_path) as reader:
        matrix = transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=helpers.LIDAR_FRAME_ID,
            target_frame_id=target_frame_id,
            timestamp_ns=1_050_000_000,
            static_transforms=[],
        )

    assert matrix is None


def test_transform_to_target_frame__not_connected(tmp_path: Path) -> None:
    # No static transforms are given and the recording has no `/tf` topic.
    mcap_path = helpers.write_mcap(path=tmp_path / "recording.mcap")

    with McapFileReader(mcap_path) as reader, pytest.raises(TransformNotFoundError):
        transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=helpers.LIDAR_FRAME_ID,
            target_frame_id=helpers.WORLD_FRAME_ID,
            timestamp_ns=1_050_000_000,
            static_transforms=[],
        )
