"""Example of indexing MCAP robotics recordings into a dataset, resolvers only.

`example_mcap_sequence.py` does the same thing through the `lightly_studio` Python API
(`ls.McapDataset`, `ls.CreateMcap`, ...). This version calls the resolver layer that API
is built on, for the case where that convenience layer is not available:

1. creates a dataset with the group slots of `COMPONENTS`, five cameras and three
   lidars, matching what a full bag looks like once it has been indexed,
2. adds a recording to it and stores the calibration of every camera,
3. pairs every sensor's frame with the sweep of `ANCHOR_COMPONENT` closest in time to
   it, and
4. writes one group per sweep that every sensor was paired to, ordered by a sequence.

A group holds a locator per component, never a decoded frame or point cloud. The
locator names the MCAP channel and the times to seek to, so the payload is read from
the recording only when it is needed. A sweep of `ANCHOR_COMPONENT` that some other
sensor has no frame close enough to gets no group at all, so every written group is
complete over all of `COMPONENTS`.

Set the topics on `COMPONENTS` below to the sensors of your own recording, and
`mcap_path` to an indexed `.mcap` file to run it. The path can also be a URI into
object storage, e.g. `s3://my-bucket/perception.mcap`; it is stored on the recording as
given, so a relative path stops working once the working directory changes.

Every step is timed, and its duration is printed as soon as it finishes, so a slow step
is visible while the run is still going. The write resolvers take lists and commit once
per call, so a whole recording is written with four calls, not four per sweep.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Iterator
from typing import NamedTuple
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap import matching
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import FrameLocator
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


class Component(NamedTuple):
    """One slot of the group, with the topics it is filled from."""

    name: str
    """The name the slot is shown and looked up under, e.g. in `group["front"]`."""

    mcap_data_type: McapDataType
    """Whether the slot holds video frames or a point cloud."""

    topic: str
    """The topic the slot's frame locators are read from."""

    camera_info_topic: str | None
    """The topic the intrinsics and the frame id of a camera are read from.

    `None` for a lidar, whose point clouds carry their frame id in the message payload
    instead, which the access layer does not read; `frame_id` names it there.
    """

    frame_id: str | None
    """The static frame id of a lidar's point clouds. `None` for a camera, whose frame
    id is read from `camera_info_topic` instead."""


# The slots of every group, in the order they are laid out: the five cameras first, so
# that a grid preview starts with them, then the three lidars. The channel of a slot is
# its position here, which is what the sensors of one bag look like once it has been
# indexed. `index_recording` fills the channel and the frame id of every slot from the
# recording itself; `COMPONENTS` only names the topics to read them from.
COMPONENTS = [
    Component(
        name="front",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/Main/compressed_video",
        camera_info_topic="/hal/perception/Main/camera_info",
        frame_id=None,
    ),
    Component(
        name="mast_left_side",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastLeftSide/compressed_video",
        camera_info_topic="/hal/perception/MastLeftSide/camera_info",
        frame_id=None,
    ),
    Component(
        name="mast_left_rear",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastLeftRear/compressed_video",
        camera_info_topic="/hal/perception/MastLeftRear/camera_info",
        frame_id=None,
    ),
    Component(
        name="mast_right_side",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastRightSide/compressed_video",
        camera_info_topic="/hal/perception/MastRightSide/camera_info",
        frame_id=None,
    ),
    Component(
        name="mast_right_rear",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/hal/perception/MastRightRear/compressed_video",
        camera_info_topic="/hal/perception/MastRightRear/camera_info",
        frame_id=None,
    ),
    Component(
        name="pcl_front",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/livox/lidar_front_left/self_filtered",
        camera_info_topic=None,
        frame_id="livox_front_left",
    ),
    Component(
        name="pcl_rear_left",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/livox/lidar_rear_left/self_filtered",
        camera_info_topic=None,
        frame_id="livox_rear_left",
    ),
    Component(
        name="pcl_rear_right",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/livox/lidar_rear_right/self_filtered",
        camera_info_topic=None,
        frame_id="livox_rear_right",
    ),
]

# The component whose sweeps a group is written per, and every other sensor is paired
# to. The front-left lidar, because it is the one `example_mcap_sequence.py` and the
# benchmark also treat as the clock of the sequence.
ANCHOR_COMPONENT = next(component for component in COMPONENTS if component.name == "pcl_front")


@contextlib.contextmanager
def timed(label: str, durations_s: dict[str, float]) -> Iterator[None]:
    """Times the wrapped block, records how long it took, and prints it right away.

    Printing here, instead of only from the summary table at the end, is what makes a
    slow step visible while it is still running the next time, rather than only after
    the whole script finishes.

    Args:
        label: The key the duration is recorded under. A repeated label is overwritten.
        durations_s: The mapping the duration in seconds is written to.

    Yields:
        Once, with the timer running.
    """
    print(f"  {label} ...", flush=True)
    start_s = time.perf_counter()
    try:
        yield
    finally:
        duration_s = time.perf_counter() - start_s
        durations_s[label] = duration_s
        print(f"  {label:<38} {duration_s:8.3f} s", flush=True)


def create_dataset(
    session: Session, name: str
) -> tuple[CollectionTable, CollectionTable, dict[str, CollectionTable]]:
    """Create a dataset with the group slots of `COMPONENTS`.

    The channel and the frame id of every slot are left unset. `index_recording` fills
    them once the first recording is indexed.

    Args:
        session: The database session to use.
        name: The name of the dataset.

    Returns:
        The root (sequence) collection, the group collection, and the component
        collections, keyed by `Component.name`.
    """
    root_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(name=name, sample_type=SampleType.SEQUENCE),
    )
    group_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=f"{name}_groups",
            parent_collection_id=root_collection.collection_id,
            sample_type=SampleType.GROUP,
        ),
    )
    component_collections = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group_collection.collection_id,
        components=[(component.name, SampleType.MCAP) for component in COMPONENTS],
    )
    for component in COMPONENTS:
        mcap_group_component_definition_resolver.create(
            session=session,
            collection_id=component_collections[component.name].collection_id,
            mcap_data_type=component.mcap_data_type,
        )
    return root_collection, group_collection, component_collections


def index_recording(  # noqa: PLR0913
    session: Session,
    root_collection: CollectionTable,
    group_collection: CollectionTable,
    component_collections: dict[str, CollectionTable],
    mcap_path: str,
    step_durations_s: dict[str, float],
) -> UUID:
    """Index one recording into a dataset.

    Args:
        session: The database session to use.
        root_collection: The dataset's root (sequence) collection, from `create_dataset`.
        group_collection: The dataset's group collection, from `create_dataset`.
        component_collections: The dataset's component collections, from `create_dataset`.
        mcap_path: The path or URI of the `.mcap` file.
        step_durations_s: The mapping the duration of each step is recorded to.

    Returns:
        The sample id of the sequence that holds the groups of the recording, in order.
    """
    print("  1. open recording ...", flush=True)
    open_start_s = time.perf_counter()
    with McapFileReader(mcap_path) as reader:
        # Opening the recording reads its index, so it is timed like the steps below.
        open_duration_s = time.perf_counter() - open_start_s
        step_durations_s["1. open recording"] = open_duration_s
        print(f"  {'1. open recording':<38} {open_duration_s:8.3f} s", flush=True)

        # Loaded together, so that a chunk shared by several topics is fetched once.
        with timed("2. locate anchor sweeps", step_durations_s):
            reader.load_data_for_topics(
                [component.topic for component in COMPONENTS]
                + [
                    component.camera_info_topic
                    for component in COMPONENTS
                    if component.camera_info_topic is not None
                ]
            )
            anchor_sweeps = reader.get_frame_locators(ANCHOR_COMPONENT.topic)

        # Every other sensor is synced to the anchor's sweep times, one call per topic.
        with timed("3. pair every sensor to the anchor", step_durations_s):
            sync_timestamps = [sweep.log_time_ns for sweep in anchor_sweeps]
            locators_by_component = {
                component.name: (
                    anchor_sweeps
                    if component is ANCHOR_COMPONENT
                    else reader.get_frame_locators(
                        component.topic,
                        sync_timestamps=sync_timestamps,
                        sync_rule=matching.closest(max_diff_ns=MAX_PAIRING_DIFF_NS),
                    )
                )
                for component in COMPONENTS
            }

        with timed("4. read camera intrinsics", step_durations_s):
            intrinsics_by_component = {
                component.name: reader.get_intrinsic(topic=component.camera_info_topic)
                for component in COMPONENTS
                if component.camera_info_topic is not None
            }

    # The recording comes first, so that its calibration can be stored before any group
    # refers to it.
    with timed("5. create recording and calibrations", step_durations_s):
        recording_id = recording_resolver.create(
            session=session,
            dataset_id=root_collection.dataset_id,
            uri=mcap_path,
            format_=RecordingFormat.MCAP,
        )
        sensor_calibration_resolver.create_many(
            session=session,
            rows=[
                SensorCalibrationCreate(
                    recording_id=recording_id,
                    collection_id=component_collections[component.name].collection_id,
                    width=intrinsics_by_component[component.name].width,
                    height=intrinsics_by_component[component.name].height,
                    k=list(intrinsics_by_component[component.name].camera_matrix),
                )
                for component in COMPONENTS
                if component.camera_info_topic is not None
            ],
        )

    # The first recording that is indexed fills the channel and the frame of each
    # component. A later recording does not change them.
    with timed("6. fill component channel and frame ids", step_durations_s):
        for component in COMPONENTS:
            first_locator = next(
                (locator for locator in locators_by_component[component.name] if locator), None
            )
            frame_id = (
                intrinsics_by_component[component.name].frame_id
                if component.camera_info_topic is not None
                else component.frame_id
            )
            mcap_group_component_definition_resolver.update(
                session=session,
                collection_id=component_collections[component.name].collection_id,
                channel_id=first_locator.channel_id if first_locator is not None else None,
                frame_id=frame_id,
            )

    with timed("7. create sequence", step_durations_s):
        sequence_sample_id = mcap_group_sequence_resolver.create(
            session=session,
            collection_id=root_collection.collection_id,
            recording_id=recording_id,
        )

    # An anchor sweep that some sensor has no frame close enough to has no complete
    # group, so it is dropped from every component alike.
    complete_indices = [
        index
        for index in range(len(anchor_sweeps))
        if all(
            locators_by_component[component.name][index] is not None
            for component in COMPONENTS
            if component is not ANCHOR_COMPONENT
        )
    ]
    complete_locators_by_component: dict[str, list[FrameLocator]] = {}
    for component in COMPONENTS:
        locators = locators_by_component[component.name]
        complete_locators_by_component[component.name] = []
        for index in complete_indices:
            locator = locators[index]
            # `complete_indices` only keeps sweeps every component was matched to.
            assert locator is not None
            complete_locators_by_component[component.name].append(locator)

    # The create resolvers take lists and commit once per call, so the whole recording
    # is written with one call per component instead of one per sweep. The ids come
    # back in the order they were passed in, which is what pairs them up again below.
    with timed("8. write locators", step_durations_s):
        sample_ids_by_component = {
            component.name: mcap_resolver.create_many(
                session=session,
                collection_id=component_collections[component.name].collection_id,
                samples=[
                    McapCreate(
                        channel_id=locator.channel_id,
                        log_time_ns=locator.log_time_ns,
                        capture_timestamp_ns=locator.log_time_ns,
                        keyframe_log_time_ns=locator.keyframe_log_time_ns,
                    )
                    for locator in complete_locators_by_component[component.name]
                ],
            )
            for component in COMPONENTS
        }

    with timed("9. write groups", step_durations_s):
        group_sample_ids = group_resolver.create_many(
            session=session,
            collection_id=group_collection.collection_id,
            groups=[
                {sample_ids_by_component[component.name][pair_index] for component in COMPONENTS}
                for pair_index in range(len(complete_indices))
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
                    timestamp_ns=anchor_sweeps[index].log_time_ns,
                )
                for seq_number, (group_sample_id, index) in enumerate(
                    zip(group_sample_ids, complete_indices)
                )
            ],
        )

    return sequence_sample_id


mcap_path = "C:\\Users\\horatiu\\Downloads\\rosbag2_2026_09_15-06_54_23_0.mcap"
db_manager.connect(cleanup_existing=True)
db_session = db_manager.persistent_session()

# The duration of every step, in the order the steps run. Printing is left out of the
# timings, only the reads and the writes are measured.
step_durations_s: dict[str, float] = {}
total_start_s = time.perf_counter()

with timed("0. create dataset schema", step_durations_s):
    root_collection, group_collection, component_collections = create_dataset(
        session=db_session, name="mcap_sequence_example"
    )

sequence_sample_id = index_recording(
    session=db_session,
    root_collection=root_collection,
    group_collection=group_collection,
    component_collections=component_collections,
    mcap_path=mcap_path,
    step_durations_s=step_durations_s,
)

# Everything a player needs to open the recording again: the path of the bag, and the
# channel of every component, in one read and without touching a single group.
with timed("11. read sequence info", step_durations_s):
    sequence_info = mcap_group_sequence_resolver.get_info(
        session=db_session, sample_id=sequence_sample_id
    )
# The sequence was created from a recording, so it is not a classic one.
assert sequence_info is not None

print(f"\n'{root_collection.name}' is indexed from {sequence_info.recording.uri}:")
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
    preview = []
    for link in sample_links[:PREVIEW_COUNT]:
        frame_sample_id, _ = group_resolver.get_group_component_with_type(
            session=db_session, sample_id=link.sample_id, key="front"
        )
        sweep_sample_id, _ = group_resolver.get_group_component_with_type(
            session=db_session, sample_id=link.sample_id, key=ANCHOR_COMPONENT.name
        )
        # The components of an MCAP dataset always hold locators.
        if frame_sample_id is None or sweep_sample_id is None:
            continue
        frame_sample = mcap_resolver.get_by_id(session=db_session, sample_id=frame_sample_id)
        sweep_sample = mcap_resolver.get_by_id(session=db_session, sample_id=sweep_sample_id)
        assert frame_sample is not None
        assert sweep_sample is not None
        preview.append((sweep_sample, frame_sample))

print(f"\n{len(sample_links)} groups, the first {PREVIEW_COUNT} of them:")
for sweep_sample, frame_sample in preview:
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
