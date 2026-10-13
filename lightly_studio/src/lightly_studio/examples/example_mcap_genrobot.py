"""Example of how to index clips of the GenRobot 10Kh-RealOmin dataset into LightlyStudio.

10Kh-RealOmin-OpenData (https://huggingface.co/datasets/genrobot2025/10Kh-RealOmin-OpenData)
holds bimanual household clips recorded with two handheld DAS grippers, one protobuf MCAP
file per clip:

    <task>/<skill>/<batch>/<clip>.mcap, e.g. Organize_Clutter/fold_towel/00001/00001.mcap

Each gripper records a fisheye camera as H.264 in `CompressedImage` messages, with its
calibration. `robot0` is the left gripper and `robot1` the right one.

One clip becomes one sequence of groups. Every frame of the left camera is a tick, and
the frame of the right camera is paired to it.

The dataset is gated. Accept its terms on Hugging Face, then download a few clips:

```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="genrobot2025/10Kh-RealOmin-OpenData",
    repo_type="dataset",
    allow_patterns=["Organize_Clutter/fold_towel/00001/0000[1-5].mcap"],
    local_dir="datasets/genrobot",
)
```

Set `EXAMPLES_GENROBOT_PATH` to the download folder to run this. Some task folders have
brackets in their name, e.g. `Clutter Tidy-Up [Stage2]`. A path with brackets is read as
a glob pattern and finds no file, so give a folder above it instead.
"""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio.database import db_manager

COMPONENTS = [
    ls.McapComponentSpec(
        name=name,
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic=f"/{robot}/sensor/camera0/compressed",
        camera_info_topic=f"/{robot}/sensor/camera0/camera_info",
    )
    for name, robot in [("left", "robot0"), ("right", "robot1")]
]

SYNC_COMPONENT = "left"

# The cameras run at 30 Hz on independent clocks, so a frame is at most half a frame
# interval away from a tick.
MAX_PAIRING_DIFF_NS = 20_000_000

env = Env()
env.read_env()
# genrobot_path = env.str("EXAMPLES_GENROBOT_PATH", "datasets/genrobot")
genrobot_path = r"C:\Users\horatiu\Downloads\00004.mcap"

db_manager.connect(cleanup_existing=True)
dataset = ls.McapDataset.load_or_create(components=COMPONENTS, name="genrobot_10kh")
dataset.add_mcaps_from_path(
    path=genrobot_path,
    sync_component=SYNC_COMPONENT,
    components=COMPONENTS,
    max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
)

for sequence in dataset.get_sequences():
    recording = dataset.get_recording(recording_id=sequence.recording_id)
    print(f"{len(sequence.get_samples())} groups indexed from {recording.uri}")

ls.start_gui()
