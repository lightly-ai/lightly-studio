"""Index an MCAP recording into a sequence of complete sensor groups, via resolvers.

Each group holds a locator per component in `COMPONENTS`, never a decoded frame or
point cloud. A sweep of `ANCHOR_COMPONENT` that any other sensor cannot pair to is
dropped, so every written group is complete.

Set `COMPONENTS` to the sensors of your recording and `EXAMPLES_MCAP_PATH` to an
indexed `.mcap` file (or a URI such as `s3://my-bucket/perception.mcap`). The path is
stored on the recording as given.

Every step is timed and printed as it finishes. Writes take lists and commit once per
call, so a recording is written with four calls, not four per sweep.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import NamedTuple
from uuid import UUID

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
from lightly_studio.core.mcap import matching
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import CameraIntrinsics, FrameLocator
from lightly_studio.database import db_manager
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.models.mcap import McapCreate
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sensor_calibration import SensorCalibrationCreate
from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import (
    collection_resolver,
    group_resolver,
    mcap_group_component_definition_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    recording_resolver,
    sensor_calibration_resolver,
    sequence_resolver,
)

# The largest time difference that still pairs a sensor's frame with an anchor sweep.
MAX_PAIRING_DIFF_NS = 50_000_000

# How many groups to print at the end.
PREVIEW_COUNT = 50


@dataclass(frozen=True)
class Component:
    """One slot of the group, with the topics it is filled from."""

    name: str
    mcap_data_type: McapDataType
    topic: str
    camera_info_topic: str | None = None
    frame_id: str | None = None

    @property
    def is_camera(self) -> bool:
        """Whether this slot is a camera. Lidars set `frame_id` instead."""
        return self.camera_info_topic is not None


# Five cameras first, so a grid preview starts with them, then the three lidars. The
# channel of a slot is its position here; `index_recording` fills channel and frame id
# from the recording.
COMPONENTS = [
    Component(
        name="front",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/Main/compressed_video",
        camera_info_topic="/hal/perception/Main/camera_info",
    ),
    Component(
        name="mast_left_side",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastLeftSide/compressed_video",
        camera_info_topic="/hal/perception/MastLeftSide/camera_info",
    ),
    Component(
        name="mast_left_rear",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastLeftRear/compressed_video",
        camera_info_topic="/hal/perception/MastLeftRear/camera_info",
    ),
    Component(
        name="mast_right_side",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastRightSide/compressed_video",
        camera_info_topic="/hal/perception/MastRightSide/camera_info",
    ),
    Component(
        name="mast_right_rear",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastRightRear/compressed_video",
        camera_info_topic="/hal/perception/MastRightRear/camera_info",
    ),
    Component(
        name="pcl_front",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/livox/lidar_front_left/self_filtered",
        frame_id="livox_front_left",
    ),
    Component(
        name="pcl_rear_left",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/livox/lidar_rear_left/self_filtered",
        frame_id="livox_rear_left",
    ),
    Component(
        name="pcl_rear_right",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/livox/lidar_rear_right/self_filtered",
        frame_id="livox_rear_right",
    ),
]
ANCHOR_COMPONENT = next(component for component in COMPONENTS if component.name == "pcl_front")


class DatasetSchema(NamedTuple):
    """The collections of an MCAP sequence dataset."""

    root: CollectionTable
    groups: CollectionTable
    components: dict[str, CollectionTable]


def create_dataset(session: Session, name: str) -> DatasetSchema:
    """Create a dataset with the group slots of `COMPONENTS`.

    Channel and frame id of every slot are left unset until `index_recording` fills
    them from the first recording.
    """
    root = collection_resolver.create(
        session=session,
        collection=CollectionCreate(name=name, sample_type=SampleType.SEQUENCE),
    )
    groups = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=f"{name}_groups",
            parent_collection_id=root.collection_id,
            sample_type=SampleType.GROUP,
        ),
    )
    components = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=groups.collection_id,
        components=[(component.name, SampleType.MCAP) for component in COMPONENTS],
    )
    for component in COMPONENTS:
        mcap_group_component_definition_resolver.create(
            session=session,
            collection_id=components[component.name].collection_id,
            mcap_data_type=component.mcap_data_type,
        )
    return DatasetSchema(root=root, groups=groups, components=components)


def index_recording(
    session: Session,
    dataset: DatasetSchema,
    mcap_path: str,
    step_durations_s: dict[str, float],
) -> UUID:
    """Index one recording into a dataset. Returns the sequence sample id."""
    loaded = _read_mcap(mcap_path=mcap_path, step_durations_s=step_durations_s)

    with timed("5. create recording and calibrations", step_durations_s):
        recording_id = recording_resolver.create(
            session=session,
            dataset_id=dataset.root.dataset_id,
            uri=mcap_path,
            format_=RecordingFormat.MCAP,
        )
        sensor_calibration_resolver.create_many(
            session=session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=recording_id,
                    collection_id=dataset.components[component.name].collection_id,
                    width=loaded.intrinsics[component.name].width,
                    height=loaded.intrinsics[component.name].height,
                    k=list(loaded.intrinsics[component.name].camera_matrix),
                )
                for component in COMPONENTS
                if component.is_camera
            ],
        )

    with timed("6. fill component channel and frame ids", step_durations_s):
        for component in COMPONENTS:
            first_locator = next(
                (locator for locator in loaded.locators[component.name] if locator), None
            )
            frame_id = (
                loaded.intrinsics[component.name].frame_id
                if component.is_camera
                else component.frame_id
            )
            mcap_group_component_definition_resolver.update(
                session=session,
                collection_id=dataset.components[component.name].collection_id,
                channel_id=first_locator.channel_id if first_locator is not None else None,
                frame_id=frame_id,
            )

    with timed("7. create sequence", step_durations_s):
        sequence_sample_id = mcap_group_sequence_resolver.create(
            session=session,
            collection_id=dataset.root.collection_id,
            recording_id=recording_id,
        )

    complete_rows = _complete_rows(locators_by_component=loaded.locators)

    with timed("8. write locators", step_durations_s):
        sample_ids_by_component = {
            component.name: mcap_resolver.create_many(
                session=session,
                collection_id=dataset.components[component.name].collection_id,
                samples=[_mcap_create(row[component.name]) for row in complete_rows],
            )
            for component in COMPONENTS
        }

    with timed("9. write groups", step_durations_s):
        group_sample_ids = group_resolver.create_many(
            session=session,
            collection_id=dataset.groups.collection_id,
            groups=[
                {sample_ids_by_component[component.name][pair_index] for component in COMPONENTS}
                for pair_index in range(len(complete_rows))
            ],
        )

    with timed("10. link groups into the sequence", step_durations_s):
        sequence_resolver.add_samples(
            session=session,
            sequence_sample_id=sequence_sample_id,
            links=[
                SampleSequenceLinkCreate(
                    sample_id=group_sample_id,
                    seq_number=seq_number,
                    timestamp_ns=row[ANCHOR_COMPONENT.name].log_time_ns,
                )
                for seq_number, (group_sample_id, row) in enumerate(
                    zip(group_sample_ids, complete_rows)
                )
            ],
        )

    return sequence_sample_id


class _LoadedRecording(NamedTuple):
    """Locators paired to the anchor, plus camera intrinsics, from one MCAP file."""

    locators: dict[str, list[FrameLocator | None]]
    intrinsics: dict[str, CameraIntrinsics]


def _read_mcap(mcap_path: str, step_durations_s: dict[str, float]) -> _LoadedRecording:
    """Open the recording, pair every sensor to the anchor, and read camera intrinsics."""
    with contextlib.ExitStack() as stack:
        with timed("1. open recording", step_durations_s):
            reader = stack.enter_context(McapFileReader(mcap_path))

        with timed("2. locate anchor sweeps", step_durations_s):
            topics = [component.topic for component in COMPONENTS]
            topics.extend(
                component.camera_info_topic
                for component in COMPONENTS
                if component.camera_info_topic is not None
            )
            reader.load_data_for_topics(topics)
            anchor_sweeps = reader.get_frame_locators(ANCHOR_COMPONENT.topic)

        with timed("3. pair every sensor to the anchor", step_durations_s):
            sync_timestamps = [sweep.log_time_ns for sweep in anchor_sweeps]
            locators: dict[str, list[FrameLocator | None]] = {}
            for component in COMPONENTS:
                if component is ANCHOR_COMPONENT:
                    locators[component.name] = list(anchor_sweeps)
                else:
                    locators[component.name] = reader.get_frame_locators(
                        component.topic,
                        sync_timestamps=sync_timestamps,
                        sync_rule=matching.closest(max_diff_ns=MAX_PAIRING_DIFF_NS),
                    )

        with timed("4. read camera intrinsics", step_durations_s):
            intrinsics = {
                component.name: reader.get_intrinsic(topic=component.camera_info_topic)
                for component in COMPONENTS
                if component.camera_info_topic is not None
            }

    return _LoadedRecording(locators=locators, intrinsics=intrinsics)


def _complete_rows(
    locators_by_component: Mapping[str, Sequence[FrameLocator | None]],
) -> list[dict[str, FrameLocator]]:
    """Keep only sweeps that have a locator for every component."""
    names = [component.name for component in COMPONENTS]
    rows: list[dict[str, FrameLocator]] = []
    for locators in zip(*(locators_by_component[name] for name in names)):
        row = {name: locator for name, locator in zip(names, locators) if locator is not None}
        if len(row) == len(COMPONENTS):
            rows.append(row)
    return rows


def _mcap_create(locator: FrameLocator) -> McapCreate:
    return McapCreate(
        channel_id=locator.channel_id,
        log_time_ns=locator.log_time_ns,
        capture_timestamp_ns=locator.log_time_ns,
        keyframe_log_time_ns=locator.keyframe_log_time_ns,
    )


@contextlib.contextmanager
def timed(label: str, durations_s: dict[str, float]) -> Iterator[None]:
    """Time the wrapped block, record it, and print the duration right away."""
    print(f"  {label} ...", flush=True)
    start_s = time.perf_counter()
    try:
        yield
    finally:
        duration_s = time.perf_counter() - start_s
        durations_s[label] = duration_s
        print(f"  {label:<38} {duration_s:8.3f} s", flush=True)


env = Env()
env.read_env()
# Read as a string, not as a path, so a URI such as `s3://...` survives unchanged.
mcap_path = env.str("EXAMPLES_MCAP_PATH", "datasets/perception.mcap")
db_manager.connect(cleanup_existing=True)
db_session = db_manager.persistent_session()

step_durations_s: dict[str, float] = {}
total_start_s = time.perf_counter()

with timed("0. create dataset schema", step_durations_s):
    dataset = create_dataset(session=db_session, name="mcap_sequence_example")

sequence_sample_id = index_recording(
    session=db_session,
    dataset=dataset,
    mcap_path=mcap_path,
    step_durations_s=step_durations_s,
)

with timed("11. read sequence info", step_durations_s):
    sequence_info = mcap_group_sequence_resolver.get_info(
        session=db_session, sample_id=sequence_sample_id
    )
assert sequence_info is not None

print(f"\n'{dataset.root.name}' is indexed from {sequence_info.recording.uri}:")
for component in sequence_info.components:
    print(
        f"  {component.group_component_index}. {component.group_component_name:<12} "
        f"{component.mcap_data_type.value:<12} channel {component.channel_id}, "
        f"frame '{component.frame_id}'"
    )

with timed("12. read back groups", step_durations_s):
    sample_links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )
    frame_sample_ids: list[UUID] = []
    sweep_sample_ids: list[UUID] = []
    for link in sample_links[:PREVIEW_COUNT]:
        frame_sample_id, _ = group_resolver.get_group_component_with_type(
            session=db_session, sample_id=link.sample_id, key="front"
        )
        sweep_sample_id, _ = group_resolver.get_group_component_with_type(
            session=db_session, sample_id=link.sample_id, key=ANCHOR_COMPONENT.name
        )
        if frame_sample_id is None or sweep_sample_id is None:
            continue
        frame_sample_ids.append(frame_sample_id)
        sweep_sample_ids.append(sweep_sample_id)
    frame_samples = mcap_resolver.get_many_by_id(session=db_session, sample_ids=frame_sample_ids)
    sweep_samples = mcap_resolver.get_many_by_id(session=db_session, sample_ids=sweep_sample_ids)

print(f"\n{len(sample_links)} groups, the first {PREVIEW_COUNT} of them:")
for sweep_sample, frame_sample in zip(sweep_samples, frame_samples):
    print(
        f"  sweep {sweep_sample.log_time_ns} on channel {sweep_sample.channel_id} "
        f"-> frame {frame_sample.log_time_ns} on channel {frame_sample.channel_id} "
        f"(decode from keyframe {frame_sample.keyframe_log_time_ns})"
    )

total_duration_s = time.perf_counter() - total_start_s
print("\nProcessing time:")
for label, duration_s in step_durations_s.items():
    print(f"  {label:<38} {duration_s:8.3f} s")
print(f"  {'total':<38} {total_duration_s:8.3f} s")
ls.start_gui()
