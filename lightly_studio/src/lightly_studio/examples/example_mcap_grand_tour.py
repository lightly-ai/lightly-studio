"""Shows GrandTour MCAP clips from a legged robot in LightlyStudio.

The clips (https://huggingface.co/datasets/lightly-ai/grand_tour_mcap_clips) are short ROS 2
recordings from the GrandTour dataset of an ANYmal robot. Each clip has three cameras
(front, left, right), two lidars (Hesai, Livox) and the robot transforms, all at 10 Hz.

Usage:
    1. Go to the `lightly_studio` folder.
    2. Download the clips:

        uv run hf download lightly-ai/grand_tour_mcap_clips --repo-type dataset --local-dir datasets/grand_tour

    3. Run the example:

        uv run src/lightly_studio/examples/example_mcap_grand_tour.py

To use other MCAP files, set `EXAMPLES_GRAND_TOUR_MCAP_PATH` to a file or a folder.
"""  # noqa: E501

from __future__ import annotations

import fsspec
from environs import Env

import lightly_studio as ls
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.database import db_manager

COMPONENTS = [
    ls.McapComponentSpec(
        name="front",
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic="/gt_box/hdr_front/image_raw/compressed",
        camera_info_topic="/gt_box/hdr_front/camera_info",
    ),
    ls.McapComponentSpec(
        name="hesai",
        mcap_data_type=ls.McapDataType.POINT_CLOUD,
        topic="/gt_box/hesai/points",
        frame_id="hesai_lidar",
    ),
    ls.McapComponentSpec(
        name="livox",
        mcap_data_type=ls.McapDataType.POINT_CLOUD,
        topic="/gt_box/livox/lidar",
        frame_id="livox_lidar",
    ),
]

# Indexed only when the input has the topic.
EXTRA_CAMERAS = [
    ls.McapComponentSpec(
        name=name,
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic=f"/gt_box/hdr_{name}/image_raw/compressed",
        camera_info_topic=f"/gt_box/hdr_{name}/camera_info",
    )
    for name in ["left", "right"]
]

TF_STATIC_TOPIC = "/tf_static"
REFERENCE_FRAME_IDS = ["base", "odom"]

SYNC_COMPONENT = "hesai"

# Half a frame at 10 Hz.
MAX_PAIRING_DIFF_NS = 50_000_000


def _topic_names(path: str) -> set[str]:
    """Returns the topics of the MCAP file at `path`, or of the first MCAP file in it."""
    filesystem, path_in_filesystem = fsspec.url_to_fs(path)
    mcap_file = path
    if filesystem.isdir(path_in_filesystem):
        first = min(filesystem.glob(f"{path_in_filesystem.rstrip('/')}/**/*.mcap"))
        mcap_file = filesystem.unstrip_protocol(first)
    with McapFileReader(mcap_file) as reader:
        return {topic.name for topic in reader.get_topics()}


env = Env()
env.read_env()
mcap_path = env.str("EXAMPLES_GRAND_TOUR_MCAP_PATH", "datasets/grand_tour")

topics = _topic_names(path=mcap_path)
components = COMPONENTS + [camera for camera in EXTRA_CAMERAS if camera.topic in topics]
reference_frame_ids = REFERENCE_FRAME_IDS if TF_STATIC_TOPIC in topics else None
print(
    f"Components: {[component.name for component in components]}, "
    f"reference frames: {reference_frame_ids}"
)

db_manager.connect(cleanup_existing=True)
dataset = ls.McapDataset.load_or_create(components=components, name="grand_tour")
dataset.add_mcaps_from_path(
    path=mcap_path,
    sync_component=SYNC_COMPONENT,
    components=components,
    max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    reference_frame_ids=reference_frame_ids,
)

for sequence in dataset.get_sequences():
    recording = dataset.get_recording(recording_id=sequence.recording_id)
    print(f"{len(sequence.get_samples())} groups indexed from {recording.uri}")

ls.start_gui()
