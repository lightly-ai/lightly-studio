"""Example of how to index MCAP recordings into a LightlyStudio dataset.

One recording becomes one sequence of groups. Every message of the sync component is
a tick, the other components are paired against the tick closest in time, and a tick
that any component cannot be paired to is dropped, so every group is complete. A group
holds a locator per component, never a decoded frame or point cloud. The locator names
the MCAP channel and the times to seek to, so the payload is read from the recording
only when it is needed.

Set `COMPONENTS` to the sensors of your own recordings and `EXAMPLES_MCAP_PATH` to a
folder of indexed `.mcap` files to run it. The path can also be a URI into object
storage, e.g. `s3://my-bucket/bags/`; it is stored on the recording as given, so a
relative path stops working once the working directory changes.
"""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio.core.mcap.mcap_sample import McapSample
from lightly_studio.database import db_manager

# The cameras come first, so that a grid preview starts with them, then the lidars. A
# camera reads its coordinate frame from `camera_info_topic`; a lidar names it here,
# because it is part of the message payload, which the access layer does not read.
COMPONENTS = [
    ls.McapComponentSpec(
        name="front",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/Main/compressed_video",
        camera_info_topic="//Main/camera_info",
    ),
    ls.McapComponentSpec(
        name="mast_left_side",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/MastLeftSide/compressed_video",
        camera_info_topic="/MastLeftSide/camera_info",
    ),
    ls.McapComponentSpec(
        name="pcl_front",
        mcap_data_type=ls.McapDataType.POINT_CLOUD,
        topic="/lidar_front_left/self_filtered",
        frame_id="lidar_front_left",
    ),
]

# The component whose messages are the ticks of a sequence, usually the slowest sensor.
SYNC_COMPONENT = "pcl_front"

# The largest time difference that still pairs a component with a tick of the sync component.
MAX_PAIRING_DIFF_NS = 50_000_000

# How many groups to print at the end.
PREVIEW_COUNT = 10

env = Env()
env.read_env()
# Read as a string, not as a path, so that a URI such as `s3://my-bucket/bags/` survives
# unchanged. Set `EXAMPLES_MCAP_PATH` to a folder of indexed `.mcap` files to run this.
mcap_path = env.str("EXAMPLES_MCAP_PATH", "datasets/mcap/")

db_manager.connect(cleanup_existing=True)
dataset = ls.McapDataset.load_or_create(components=COMPONENTS, name="mcap_sequence_example")
dataset.add_mcaps_from_path(
    path=mcap_path,
    sync_component=SYNC_COMPONENT,
    components=COMPONENTS,
    max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
)

group_dataset = dataset.group_dataset
print(f"\nComponents of '{dataset.name}':")
for spec in COMPONENTS:
    component = group_dataset.get_component(name=spec.name)
    print(
        f"  {component.name:<16} {component.mcap_data_type.value:<12} "
        f"channel {component.channel_id}, frame '{component.frame_id}'"
    )

for sequence in dataset.get_sequences():
    recording = dataset.get_recording(recording_id=sequence.recording_id)
    entries = sequence.get_samples()
    print(f"\n{len(entries)} groups indexed from {recording.uri}, the first {PREVIEW_COUNT}:")
    for entry in entries[:PREVIEW_COUNT]:
        group_sample = group_dataset.get_sample(sample_id=entry.sample_id)
        frame_sample = group_sample["front"]
        sweep_sample = group_sample[SYNC_COMPONENT]
        # The components of an MCAP dataset always hold locators.
        if not isinstance(frame_sample, McapSample) or not isinstance(sweep_sample, McapSample):
            continue
        print(
            f"  sweep {sweep_sample.log_time_ns} on channel {sweep_sample.channel_id} "
            f"-> frame {frame_sample.log_time_ns} on channel {frame_sample.channel_id} "
            f"(decode from keyframe {frame_sample.keyframe_log_time_ns})"
        )

ls.start_gui()
