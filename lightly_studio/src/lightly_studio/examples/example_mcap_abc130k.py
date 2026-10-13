"""Example of how to index episodes of the ABC-130k robot dataset into LightlyStudio.

ABC-130k (https://huggingface.co/datasets/XDOF/ABC-130k) holds bimanual teleoperation
episodes as protobuf MCAP files, one folder per episode:

    data/val/task=<task_name>/episode_<id>/episode.mcap
    data/val/task=<task_name>/episode_<id>/annotation.mcap  # Annotated episodes only.

One episode becomes one sequence of groups. Every frame of the top camera is a tick,
and the frames of the two wrist cameras are paired to it. The subtask labels of
`annotation.mcap` are added as tags of the groups, so they show next to each tick.

The dataset is gated. Accept its terms on Hugging Face, then download a few episodes:

```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="XDOF/ABC-130k",
    repo_type="dataset",
    allow_patterns=["data/val/task=put_the_screwdriver_in_the_bin/*"],
    local_dir="datasets/abc-130k",
)
```

A public subset of 40 episodes is also at https://huggingface.co/datasets/Voxel51/ABC-130k.
Its files are named `episode.fo.mcap` and have no `annotation.mcap`.

Set `EXAMPLES_ABC130K_PATH` to the download folder to run this.
"""

from __future__ import annotations

import bisect
from pathlib import Path

from environs import Env

import lightly_studio as ls
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.sequence import McapSequence
from lightly_studio.database import db_manager

# Every station has a top camera and two wrist cameras. A stereo (ZED-X) station also
# records `/top-left-camera` and `/top-right-camera` at full resolution, but a mono
# (RealSense) station does not, so only `/top-camera` is in every episode.
#
# The cameras do not set `camera_info_topic`, because not every episode records the
# `/<camera>-info` calibration topics. The calibration is only used to project 3D data
# into a camera, and ABC-130k has no 3D data. The frame is named here instead.
COMPONENTS = [
    ls.McapComponentSpec(
        name="top",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/top-camera",
        frame_id="top_camera-images-rgb",
    ),
    ls.McapComponentSpec(
        name="left_wrist",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/left-wrist-camera",
        frame_id="left_camera-images-rgb",
    ),
    ls.McapComponentSpec(
        name="right_wrist",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/right-wrist-camera",
        frame_id="right_camera-images-rgb",
    ),
]

SYNC_COMPONENT = "top"

# The cameras run on independent clocks at 30 Hz or 60 Hz, so a frame is at most half
# a frame interval away from a tick.
MAX_PAIRING_DIFF_NS = 20_000_000

# The glob matches `episode.mcap` and `episode.fo.mcap`, but not `annotation.mcap`.
EPISODE_GLOB = "**/episode*.mcap"

# Each message starts a subtask, which runs until the next message.
ANNOTATION_FILENAME = "annotation.mcap"
SUBTASK_TOPIC = "/subtask-annotation"


def add_subtask_tags(dataset: ls.McapDataset, sequence: McapSequence) -> None:
    """Tag every group of a sequence with the subtask it was captured in.

    The subtasks are read from the `annotation.mcap` next to the episode. Groups
    captured before the first subtask are not tagged.

    Args:
        dataset: The dataset of the sequence.
        sequence: The sequence of one episode.
    """
    recording = dataset.get_recording(recording_id=sequence.recording_id)
    annotation_path = Path(recording.uri).with_name(ANNOTATION_FILENAME)
    if not annotation_path.exists():
        return
    with McapFileReader(annotation_path) as reader:
        subtasks = sorted(
            reader.iter_decoded_messages(topic=SUBTASK_TOPIC), key=lambda subtask: subtask[0]
        )
    start_times_ns = [log_time_ns for log_time_ns, _ in subtasks]
    for entry in sequence.get_samples():
        if entry.timestamp_ns is None:
            continue
        index = bisect.bisect_right(start_times_ns, entry.timestamp_ns) - 1
        if index < 0:
            continue
        group_sample = dataset.group_dataset.get_sample(sample_id=entry.sample_id)
        group_sample.add_tag(subtasks[index][1].data)


env = Env()
env.read_env()
abc_path = env.str("EXAMPLES_ABC130K_PATH", "datasets/abc-130k")

db_manager.connect(cleanup_existing=True)
dataset = ls.McapDataset.load_or_create(components=COMPONENTS, name="abc_130k")
dataset.add_mcaps_from_path(
    path="C:\\Users\\horatiu\\Downloads\\episode.mcap",
    sync_component=SYNC_COMPONENT,
    components=COMPONENTS,
    max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
)

for sequence in dataset.get_sequences():
    add_subtask_tags(dataset=dataset, sequence=sequence)
    recording = dataset.get_recording(recording_id=sequence.recording_id)
    print(f"{len(sequence.get_samples())} groups indexed from {recording.uri}")

ls.start_gui()
