from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.core.mcap import add_mcaps
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.core.mcap.mcap_sample import McapSample
from lightly_studio.database import db_manager
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    recording_resolver,
    sensor_calibration_resolver,
    sequence_resolver,
)
from tests.core.mcap import helpers

VIDEO_COMPONENT = "front"
POINT_CLOUD_COMPONENT = "pcl_front"

COMPONENTS = [
    McapComponentSpec(
        name=VIDEO_COMPONENT,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic=helpers.CAMERA_VIDEO_TOPIC,
        camera_info_topic=helpers.CAMERA_INFO_TOPIC,
    ),
    McapComponentSpec(
        name=POINT_CLOUD_COMPONENT,
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic=helpers.LIDAR_POINTS_TOPIC,
        frame_id=helpers.LIDAR_FRAME_ID,
    ),
]

# Each of the two lidar sweeps has a camera frame 50 ms away, so both are indexed.
MAX_PAIRING_DIFF_NS = 50_000_000


@pytest.fixture
def mcap_path(tmp_path: Path) -> Path:
    return helpers.write_mcap(tmp_path / "recording.mcap")


def test_index_recording(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    links = _get_sample_links(sequence_sample_id=sequence_sample_id)
    assert [link.timestamp_ns for link in links] == list(helpers.LIDAR_LOG_TIMES_NS)
    assert [link.seq_number for link in links] == [0, 1]


def test_index_recording__sequence_uses_capture_timestamp(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    capture_offset_ns = -50_000_000
    mcap_path = helpers.write_mcap(
        tmp_path / "offset.mcap", lidar_stamp_offset_ns=capture_offset_ns
    )
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    links = _get_sample_links(sequence_sample_id=sequence_sample_id)
    assert [link.timestamp_ns for link in links] == [
        helpers.LIDAR_LOG_TIMES_NS[0] + capture_offset_ns,
        helpers.LIDAR_LOG_TIMES_NS[1] + capture_offset_ns,
    ]


def test_index_recording__falls_back_to_log_time_when_capture_clocks_differ(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    mcap_path = helpers.write_mcap(
        tmp_path / "bad_camera_stamp.mcap", video_stamp_offset_ns=10_000_000_000
    )
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    links = _get_sample_links(sequence_sample_id=sequence_sample_id)
    assert [link.timestamp_ns for link in links] == list(helpers.LIDAR_LOG_TIMES_NS)
    assert [link.seq_number for link in links] == [0, 1]


def test_index_recording__pairs_the_closest_frame(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    links = _get_sample_links(sequence_sample_id=sequence_sample_id)
    group_dataset = dataset.group_dataset
    log_times_ns = []
    for link in links:
        group_sample = group_dataset.get_sample(sample_id=link.sample_id)
        frame_sample = group_sample[VIDEO_COMPONENT]
        assert isinstance(frame_sample, McapSample)
        log_times_ns.append(frame_sample.log_time_ns)
    # A tie is resolved in favour of the earlier frame, so the sweep at 1.05 s pairs
    # with the frame at 1.0 s and the sweep at 1.25 s with the frame at 1.2 s.
    assert log_times_ns == [
        helpers.VIDEO_LOG_TIMES_NS[0],
        helpers.VIDEO_LOG_TIMES_NS[2],
    ]


def test_index_recording__drops_unpaired_ticks(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    # No camera frame is within 1 ms of a sweep, so no group is complete.
    sequence_sample_id = add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=1_000_000,
    )

    assert _get_sample_links(sequence_sample_id=sequence_sample_id) == []
    # The channel is a property of the topic, so it is filled even with no paired ticks.
    front = dataset.group_dataset.get_component(name=VIDEO_COMPONENT)
    pcl_front = dataset.group_dataset.get_component(name=POINT_CLOUD_COMPONENT)
    assert front.channel_id is not None
    assert pcl_front.channel_id is not None


def test_index_recording__fills_the_component_definitions(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    front = dataset.group_dataset.get_component(name=VIDEO_COMPONENT)
    pcl_front = dataset.group_dataset.get_component(name=POINT_CLOUD_COMPONENT)
    assert front.channel_id is not None
    assert pcl_front.channel_id is not None
    assert front.channel_id != pcl_front.channel_id
    # The camera takes its frame from the camera info topic, the lidar from its spec.
    assert front.frame_id == helpers.CAMERA_FRAME_ID
    assert pcl_front.frame_id == helpers.LIDAR_FRAME_ID


def test_index_recording__stores_the_camera_calibration(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    session = db_manager.persistent_session()
    recordings = recording_resolver.get_all_by_dataset_id(
        session=session, dataset_id=dataset.dataset_id
    )
    assert len(recordings) == 1
    assert recordings[0].uri == str(mcap_path)
    calibrations = sensor_calibration_resolver.get_all_by_recording_id(
        session=session, recording_id=recordings[0].recording_id
    )
    assert len(calibrations) == 1
    assert calibrations[0].width == helpers.IMAGE_WIDTH
    assert calibrations[0].height == helpers.IMAGE_HEIGHT
    assert calibrations[0].k == list(helpers.CAMERA_MATRIX)


def test_index_recording__unknown_sync_component(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    with pytest.raises(ValueError, match="sync_component 'rear' is not a component"):
        add_mcaps.index_recording(
            dataset=dataset,
            mcap_path=str(mcap_path),
            sync_component="rear",
            components=COMPONENTS,
        )


def test_index_recording__after_load(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    McapDataset.create(components=COMPONENTS, name="perception")
    loaded = McapDataset.load(name="perception")

    sequence_sample_id = add_mcaps.index_recording(
        dataset=loaded,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    assert _get_sample_links(sequence_sample_id=sequence_sample_id) != []


def test_index_recording__components_do_not_match(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    with pytest.raises(ValueError, match="already exists with the components"):
        add_mcaps.index_recording(
            dataset=dataset,
            mcap_path=str(mcap_path),
            sync_component=POINT_CLOUD_COMPONENT,
            components=[COMPONENTS[0]],
        )


def test_index_recordings__continues_after_a_broken_recording(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
    tmp_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    # A recording without the topics of the components cannot be indexed.
    other_path = helpers.write_unchunked_mcap(tmp_path / "unchunked.mcap")

    sequence_sample_ids = add_mcaps.index_recordings(
        dataset=dataset,
        mcap_paths=[str(other_path), str(mcap_path)],
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    assert len(sequence_sample_ids) == 1
    assert _get_sample_links(sequence_sample_id=sequence_sample_ids[0]) != []


def test_index_recordings__all_broken(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    other_path = helpers.write_unchunked_mcap(tmp_path / "unchunked.mcap")

    with pytest.raises(AllInputFilesFailedError):
        add_mcaps.index_recordings(
            dataset=dataset,
            mcap_paths=[str(other_path)],
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
        )


def test_index_recordings__empty(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    assert (
        add_mcaps.index_recordings(
            dataset=dataset,
            mcap_paths=[],
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
        )
        == []
    )


def test_index_recordings__skips_already_present(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    first_ids = add_mcaps.index_recordings(
        dataset=dataset,
        mcap_paths=[str(mcap_path)],
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    second_ids = add_mcaps.index_recordings(
        dataset=dataset,
        mcap_paths=[str(mcap_path)],
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    assert first_ids != []
    assert second_ids == []
    recordings = recording_resolver.get_all_by_dataset_id(
        session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
    )
    assert len(recordings) == 1


def test_index_recordings__skips_duplicate_paths_in_the_same_call(
    patch_collection: None,  # noqa: ARG001
    mcap_path: Path,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    sequence_sample_ids = add_mcaps.index_recordings(
        dataset=dataset,
        mcap_paths=[str(mcap_path), str(mcap_path)],
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )

    assert len(sequence_sample_ids) == 1
    recordings = recording_resolver.get_all_by_dataset_id(
        session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
    )
    assert len(recordings) == 1


class TestMcapDatasetAddMcapsFromPath:
    def test_add_mcaps_from_path(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        helpers.write_mcap(tmp_path / "first.mcap")
        helpers.write_mcap(tmp_path / "second.mcap")
        dataset = McapDataset.create(components=COMPONENTS, name="perception")

        dataset.add_mcaps_from_path(
            path=tmp_path,
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
            max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
        )

        recordings = recording_resolver.get_all_by_dataset_id(
            session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
        )
        assert sorted(Path(recording.uri).name for recording in recordings) == [
            "first.mcap",
            "second.mcap",
        ]

    def test_add_mcaps_from_path__skips_already_present(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        helpers.write_mcap(tmp_path / "first.mcap")
        helpers.write_mcap(tmp_path / "second.mcap")
        dataset = McapDataset.create(components=COMPONENTS, name="perception")
        dataset.add_mcaps_from_path(
            path=tmp_path,
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
            max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
        )

        dataset.add_mcaps_from_path(
            path=tmp_path,
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
            max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
        )

        recordings = recording_resolver.get_all_by_dataset_id(
            session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
        )
        assert sorted(Path(recording.uri).name for recording in recordings) == [
            "first.mcap",
            "second.mcap",
        ]
        assert len(dataset.get_sequences()) == 2

    def test_add_mcaps_from_path__limit(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        helpers.write_mcap(tmp_path / "first.mcap")
        helpers.write_mcap(tmp_path / "second.mcap")
        dataset = McapDataset.create(components=COMPONENTS, name="perception")

        dataset.add_mcaps_from_path(
            path=tmp_path,
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
            max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
            limit=1,
        )

        recordings = recording_resolver.get_all_by_dataset_id(
            session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
        )
        assert len(recordings) == 1

    def test_add_mcaps_from_path__invalid_limit(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset = McapDataset.create(components=COMPONENTS, name="perception")

        with pytest.raises(ValueError, match="limit must be greater than 0"):
            dataset.add_mcaps_from_path(
                path=tmp_path,
                sync_component=POINT_CLOUD_COMPONENT,
                components=COMPONENTS,
                limit=0,
            )

    def test_add_mcaps_from_path__after_load(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        helpers.write_mcap(tmp_path / "first.mcap")
        McapDataset.create(components=COMPONENTS, name="perception")
        loaded = McapDataset.load(name="perception")

        loaded.add_mcaps_from_path(
            path=tmp_path,
            sync_component=POINT_CLOUD_COMPONENT,
            components=COMPONENTS,
            max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
        )

        recordings = recording_resolver.get_all_by_dataset_id(
            session=db_manager.persistent_session(), dataset_id=loaded.dataset_id
        )
        assert [Path(recording.uri).name for recording in recordings] == ["first.mcap"]

    def test_add_mcaps_from_path__components_do_not_match(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        McapDataset.create(components=COMPONENTS, name="perception")
        loaded = McapDataset.load(name="perception")

        with pytest.raises(ValueError, match="already exists with the components"):
            loaded.add_mcaps_from_path(
                path=tmp_path,
                sync_component=POINT_CLOUD_COMPONENT,
                components=[COMPONENTS[0]],
            )


def _get_sample_links(sequence_sample_id: UUID) -> list[SampleSequenceLinkTable]:
    """Read the slots of a sequence back, in order."""
    return sequence_resolver.get_sample_links(
        session=db_manager.persistent_session(), sequence_sample_id=sequence_sample_id
    )
