from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

from lightly_studio.core.mcap import add_labels
from lightly_studio.core.mcap.type_definitions import SceneUpdateLabels
from lightly_studio.database import db_manager
from lightly_studio.resolvers import annotation_resolver
from tests.core.mcap import helpers
from tests.export import mcap_helpers


def test_get_cuboid_frame_ids_by_sequence_ids(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(tmp_path=tmp_path)
    first_ns, second_ns = helpers.LIDAR_LOG_TIMES_NS
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=7, frame_id="odom"),
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=8, frame_id="map"),
                    )
                ),
            ),
            (
                second_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(timestamp_ns=second_ns, track_id=8, frame_id="map"),
                    )
                ),
            ),
        ],
    )
    session = db_manager.persistent_session()

    result = annotation_resolver.get_cuboid_frame_ids_by_sequence_ids(
        session=session, sequence_ids=[sequence.sample_id]
    )

    # 2 cuboids in "map", 1 in "odom".
    assert result == ["map", "odom"]


def test_get_cuboid_frame_ids_by_sequence_ids__other_sequence_is_ignored(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path / "a", dataset_name="perception_a"
    )
    _, other_sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path / "b", dataset_name="perception_b"
    )
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth_labeled.mcap",
        messages=[
            (
                timestamp_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=timestamp_ns, track_id=7),)
                ),
            )
        ],
    )
    session = db_manager.persistent_session()

    result = annotation_resolver.get_cuboid_frame_ids_by_sequence_ids(
        session=session, sequence_ids=[other_sequence.sample_id]
    )

    assert result == []


def test_get_cuboid_frame_ids_by_sequence_ids__empty_input(db_session: Session) -> None:
    result = annotation_resolver.get_cuboid_frame_ids_by_sequence_ids(
        session=db_session, sequence_ids=[]
    )

    assert result == []
