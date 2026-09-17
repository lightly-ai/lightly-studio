"""Example of indexing MCAP robotics recordings into a dataset, resolvers only.

`example_mcap_sequence.py` does the same thing through the `lightly_studio` Python API
(`ls.McapDataset`, `ls.CreateMcap`, ...). This version calls the resolver layer that API
is built on, for the case where that convenience layer is not available:

1. creates a dataset with one camera component and one lidar component,
2. adds a recording to it and stores the calibration of the camera,
3. pairs each lidar sweep with the camera frame closest in time to it, and
4. writes one group per sweep, ordered by a sequence.

A group holds a locator per component, never a decoded frame or point cloud. The
locator names the MCAP channel and the times to seek to, so the payload is read from
the recording only when it is needed.

Set the topic constants below to the lidar and the camera of your own recording, and
`EXAMPLES_MCAP_PATH` to an indexed `.mcap` file to run it. The path can also be a URI
into object storage, e.g. `s3://my-bucket/perception.mcap`; it is stored on the
recording as given, so a relative path stops working once the working directory
changes.

Every step is timed, and its duration is printed as soon as it finishes, so a slow step
is visible while the run is still going. The write resolvers take lists and commit once
per call, so a whole recording is written with four calls, not four per sweep.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Iterator
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap import matching
from lightly_studio.core.mcap.reader import McapFileReader
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

# The lidar and the camera to pair, and the topic the calibration is published on.
POINT_CLOUD_TOPIC = "/livox/lidar_front_left/self_filtered"
VIDEO_TOPIC = "/hal/perception/Main/compressed_video"
CAMERA_INFO_TOPIC = "/hal/perception/Main/camera_info"

# The coordinate frame the point clouds of POINT_CLOUD_TOPIC are recorded in. It is
# part of the message payload, which the access layer does not read, so it is named
# here. The camera frame comes from the camera info topic.
POINT_CLOUD_FRAME_ID = "livox_front_left"

# The largest time difference that still pairs a camera frame with a lidar sweep.
MAX_PAIRING_DIFF_NS = 50_000_000

# The names the components are shown and looked up under.
VIDEO_COMPONENT = "front"
POINT_CLOUD_COMPONENT = "pcl_front"

# How many groups to print at the end.
PREVIEW_COUNT = 50


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
    """Create a dataset with one video-frame component and one point-cloud component.

    Args:
        session: The database session to use.
        name: The name of the dataset.

    Returns:
        The root (sequence) collection, the group collection, and the component
        collections, keyed by `VIDEO_COMPONENT` and `POINT_CLOUD_COMPONENT`.
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
        components=[
            (VIDEO_COMPONENT, SampleType.MCAP),
            (POINT_CLOUD_COMPONENT, SampleType.MCAP),
        ],
    )
    for component_name, mcap_data_type in [
        (VIDEO_COMPONENT, McapDataType.VIDEO_FRAME),
        (POINT_CLOUD_COMPONENT, McapDataType.POINT_CLOUD),
    ]:
        mcap_group_component_definition_resolver.create(
            session=session,
            collection_id=component_collections[component_name].collection_id,
            mcap_data_type=mcap_data_type,
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
    front_collection_id = component_collections[VIDEO_COMPONENT].collection_id
    pcl_front_collection_id = component_collections[POINT_CLOUD_COMPONENT].collection_id

    print("  1. open recording ...", flush=True)
    open_start_s = time.perf_counter()
    with McapFileReader(mcap_path) as reader:
        # Opening the recording reads its index, so it is timed like the steps below.
        open_duration_s = time.perf_counter() - open_start_s
        step_durations_s["1. open recording"] = open_duration_s
        print(f"  {'1. open recording':<38} {open_duration_s:8.3f} s", flush=True)

        # Locate the sweeps and the frames in a single pass. Reading the two topics
        # separately would fetch the chunks they share twice.
        with timed("2. locate sweeps and frames", step_durations_s):
            reader.load_data_for_topics([POINT_CLOUD_TOPIC, VIDEO_TOPIC, CAMERA_INFO_TOPIC])
            sweeps = reader.get_frame_locators(POINT_CLOUD_TOPIC)

        with timed("3. pair camera frames", step_durations_s):
            frames = reader.get_frame_locators(
                VIDEO_TOPIC,
                sync_timestamps=[sweep.log_time_ns for sweep in sweeps],
                sync_rule=matching.closest(max_diff_ns=MAX_PAIRING_DIFF_NS),
            )

        with timed("4. read camera intrinsics", step_durations_s):
            intrinsics = reader.get_intrinsic(topic=CAMERA_INFO_TOPIC)

    # The recording comes first, so that its calibration can be stored before any group
    # refers to it.
    with timed("5. create recording and calibration", step_durations_s):
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
                    collection_id=front_collection_id,
                    width=intrinsics.width,
                    height=intrinsics.height,
                    k=list(intrinsics.camera_matrix),
                )
            ],
        )

    # The first recording that is indexed fills the channel and the frame of each
    # component. A later recording does not change them.
    with timed("6. fill component channel and frame ids", step_durations_s):
        mcap_group_component_definition_resolver.update(
            session=session,
            collection_id=front_collection_id,
            channel_id=frames[0].channel_id if frames[0] is not None else None,
            frame_id=intrinsics.frame_id,
        )
        mcap_group_component_definition_resolver.update(
            session=session,
            collection_id=pcl_front_collection_id,
            channel_id=sweeps[0].channel_id,
            frame_id=POINT_CLOUD_FRAME_ID,
        )

    with timed("7. create sequence", step_durations_s):
        sequence_sample_id = mcap_group_sequence_resolver.create(
            session=session,
            collection_id=root_collection.collection_id,
            recording_id=recording_id,
        )

    # A sweep that no camera frame is close enough to has no complete group.
    pairs = [(sweep, frame) for sweep, frame in zip(sweeps, frames) if frame is not None]

    # The create resolvers take lists and commit once per call, so the whole recording
    # is written with three calls instead of three per sweep. The ids come back in the
    # order they were passed in, which is what pairs them up again below.
    with timed("8. write locators", step_durations_s):
        frame_sample_ids = mcap_resolver.create_many(
            session=session,
            collection_id=front_collection_id,
            samples=[
                McapCreate(
                    channel_id=frame.channel_id,
                    log_time_ns=frame.log_time_ns,
                    capture_timestamp_ns=frame.log_time_ns,
                    keyframe_log_time_ns=frame.keyframe_log_time_ns,
                )
                for _, frame in pairs
            ],
        )
        sweep_sample_ids = mcap_resolver.create_many(
            session=session,
            collection_id=pcl_front_collection_id,
            samples=[
                McapCreate(
                    channel_id=sweep.channel_id,
                    log_time_ns=sweep.log_time_ns,
                    capture_timestamp_ns=sweep.log_time_ns,
                    keyframe_log_time_ns=sweep.keyframe_log_time_ns,
                )
                for sweep, _ in pairs
            ],
        )

    with timed("9. write groups", step_durations_s):
        group_sample_ids = group_resolver.create_many(
            session=session,
            collection_id=group_collection.collection_id,
            groups=[
                {frame_sample_id, sweep_sample_id}
                for frame_sample_id, sweep_sample_id in zip(frame_sample_ids, sweep_sample_ids)
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
                    timestamp_ns=sweep.log_time_ns,
                )
                for seq_number, (group_sample_id, (sweep, _)) in enumerate(
                    zip(group_sample_ids, pairs)
                )
            ],
        )

    return sequence_sample_id


mcap_path = "C:\\Users\\horatiu\\Downloads\\rosbag2_2026_08_02-20_53_11_0_output.mcap"
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
# with timed("11. read sequence info", step_durations_s):
#     sequence_info = mcap_group_sequence_resolver.get_info(
#         session=db_session, sample_id=sequence_sample_id
#     )
# # The sequence was created from a recording, so it is not a classic one.
# assert sequence_info is not None

# print(f"\n'{root_collection.name}' is indexed from {sequence_info.recording.uri}:")
# for component in sequence_info.components:
#     print(
#         f"  {component.group_component_index}. {component.group_component_name:<12} "
#         f"{component.mcap_data_type.value:<12} channel {component.channel_id}, "
#         f"frame '{component.frame_id}'"
#     )

with timed("12. read back groups", step_durations_s):
    sample_links = sequence_resolver.get_sample_links(
        session=db_session, sequence_sample_id=sequence_sample_id
    )
    preview = []
    for link in sample_links[:PREVIEW_COUNT]:
        frame_sample_id, _ = group_resolver.get_group_component_with_type(
            session=db_session, sample_id=link.sample_id, key=VIDEO_COMPONENT
        )
        sweep_sample_id, _ = group_resolver.get_group_component_with_type(
            session=db_session, sample_id=link.sample_id, key=POINT_CLOUD_COMPONENT
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
