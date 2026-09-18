"""Example of how to read an MCAP robotics recording.

The MCAP access layer answers where data is, not what it holds: it returns frame
locators, never decoded video frames or point clouds. The example pairs one lidar
with one camera of a recording:

1. locates every lidar sweep and every camera frame in a single pass,
2. pairs each sweep with the camera frame closest in time to it.

Every read is timed, and the wall-clock time of each step and of the whole run is
printed at the end.

Set the topic constants below to the lidar and the camera of your own recording, and
`EXAMPLES_MCAP_PATH` to an indexed `.mcap` file to run it. The file is read through
fsspec, so the path can also be a URI into object storage, e.g.
`s3://my-bucket/perception.mcap`. Only the summary and the chunks a step needs are
fetched, so a remote recording does not have to be downloaded first. Credentials are
read from the environment, e.g. from the `AWS_*` variables; pass `storage_options` to
`McapFileReader` to set them, or an endpoint, explicitly.

Prerequisites — install the optional extras before running::

    uv run --extra mcap python src/lightly_studio/examples/example_mcap.py
    # For S3 URIs also add: --extra cloud-storage
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Iterator

from environs import Env

from lightly_studio.core.mcap import matching
from lightly_studio.core.mcap.reader import McapFileReader

# The lidar and the camera to pair.
POINT_CLOUD_TOPIC = "/livox/lidar_front_left/self_filtered"
VIDEO_TOPIC = "/hal/perception/Main/compressed_video"

# The largest time difference that still pairs a camera frame with a lidar sweep.
MAX_PAIRING_DIFF_NS = 50_000_000

# How many entries of a list to print.
PREVIEW_COUNT = 5

NANOSECONDS_PER_MILLISECOND = 1_000_000


@contextlib.contextmanager
def timed(label: str, durations_s: dict[str, float]) -> Iterator[None]:
    """Times the wrapped block and records how long it took.

    Args:
        label: The key the duration is recorded under. A repeated label is overwritten.
        durations_s: The mapping the duration in seconds is written to.

    Yields:
        Once, with the timer running.
    """
    start_s = time.perf_counter()
    try:
        yield
    finally:
        durations_s[label] = time.perf_counter() - start_s


env = Env()
env.read_env()
# Read as a string, not as a path, so that a URI such as `s3://my-bucket/recording.mcap`
# survives unchanged. Set `EXAMPLES_MCAP_PATH` to an indexed `.mcap` file to run this.
mcap_path = env.str("EXAMPLES_MCAP_PATH", "datasets/perception.mcap")

# The duration of every step, in the order the steps run. Printing is left out of the
# timings, only the reads are measured.
step_durations_s: dict[str, float] = {}
total_start_s = time.perf_counter()

open_start_s = time.perf_counter()
with McapFileReader(mcap_path) as reader:
    # Opening the recording reads its index, so it is timed like the steps below.
    step_durations_s["0. open recording"] = time.perf_counter() - open_start_s

    # 1. The lidar sweeps and the camera frames, located in a single pass. Reading the
    # two topics separately would fetch the chunks they share twice.
    with timed("1. locate sweeps and frames", step_durations_s):
        reader.load_data_for_topics([POINT_CLOUD_TOPIC, VIDEO_TOPIC])
        sweep_locators = reader.get_frame_locators(POINT_CLOUD_TOPIC)
    sweep_timestamp_list = [locator.log_time_ns for locator in sweep_locators]
    print(f"\n{len(sweep_timestamp_list)} sweeps on '{POINT_CLOUD_TOPIC}':")
    for sweep_timestamp in sweep_timestamp_list[:PREVIEW_COUNT]:
        print(f"  log_time_ns={sweep_timestamp}")

    # 2. The camera frame that belongs to each sweep, matched from the pass above. A
    # camera frame is inter-frame compressed, so decoding it starts at the keyframe the
    # locator names.
    with timed("2. pair camera frames", step_durations_s):
        camera_frames = reader.get_frame_locators(
            VIDEO_TOPIC,
            sync_timestamps=sweep_timestamp_list,
            sync_rule=matching.closest(max_diff_ns=MAX_PAIRING_DIFF_NS),
        )
    paired = [
        (sweep_timestamp, camera_frame)
        for sweep_timestamp, camera_frame in zip(sweep_timestamp_list, camera_frames)
        if camera_frame is not None
    ]
    max_diff_ms = MAX_PAIRING_DIFF_NS / NANOSECONDS_PER_MILLISECOND
    print(
        f"\n{len(paired)} of {len(sweep_timestamp_list)} sweeps have a frame on "
        f"'{VIDEO_TOPIC}' within {max_diff_ms:.0f} ms:"
    )
    for sweep_timestamp, camera_frame in paired[:PREVIEW_COUNT]:
        diff_ms = (camera_frame.log_time_ns - sweep_timestamp) / NANOSECONDS_PER_MILLISECOND
        print(
            f"  sweep {sweep_timestamp} -> frame {camera_frame.log_time_ns} "
            f"({diff_ms:+.1f} ms, decode from keyframe {camera_frame.keyframe_log_time_ns})"
        )

total_duration_s = time.perf_counter() - total_start_s
print("\nProcessing time:")
for label, duration_s in step_durations_s.items():
    print(f"  {label:<30} {duration_s:8.3f} s")
print(f"  {'total':<30} {total_duration_s:8.3f} s")
