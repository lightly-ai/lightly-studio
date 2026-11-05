"""Example of how to index the GrandTour MCAP clips into LightlyStudio.

The clips are at https://huggingface.co/datasets/lightly-ai/grand_tour_mcap_clips. They are
short ros2 MCAP recordings from the GrandTour dataset
(https://huggingface.co/datasets/leggedrobotics/grand_tour_dataset) of an ANYmal legged
robot with the Boxi sensor payload. Each clip has these topics:

    /gt_box/hdr_{front,left,right}/image_raw/compressed  sensor_msgs/msg/CompressedImage  10 Hz
    /gt_box/hdr_{front,left,right}/camera_info           sensor_msgs/msg/CameraInfo
    /gt_box/hesai/points                                 sensor_msgs/msg/PointCloud2      10 Hz
    /gt_box/livox/lidar                                  sensor_msgs/msg/PointCloud2      10 Hz
    /tf_static                                           tf2_msgs/msg/TFMessage
    /tf                                                  tf2_msgs/msg/TFMessage  odom -> base

The three cameras and the two lidars are indexed. One recording becomes one sequence of
groups. Every Hesai point cloud is a tick, and the camera frames and the Livox point cloud
are paired to it. The viewer shows the `base` and `odom` frames.

The example reads the clips from `datasets/grand_tour/`. Download them there:

    hf download lightly-ai/grand_tour_mcap_clips --repo-type dataset --local-dir datasets/grand_tour

Or quickly read a clip directly from Hugging Face, without a download:

    EXAMPLES_GRAND_TOUR_MCAP_PATH=hf://datasets/lightly-ai/grand_tour_mcap_clips/grand_tour_2024-11-02-17-43-10.mcap

Set `EXAMPLES_GRAND_TOUR_MCAP_PATH` to an MCAP file, or to a folder of them, to use a
different path.
"""

from __future__ import annotations

import fsspec
from environs import Env

import lightly_studio as ls
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.database import db_manager

# The components of every file: the official files and the converted ones.
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

# The cameras that only the converted files have. Each is indexed when the input has its topic.
EXTRA_CAMERAS = [
    ls.McapComponentSpec(
        name=name,
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic=f"/gt_box/hdr_{name}/image_raw/compressed",
        camera_info_topic=f"/gt_box/hdr_{name}/camera_info",
    )
    for name in ["left", "right"]
]

# Frames in the viewer Frame menu when the input has `/tf_static`. The first is the default.
# `base` is the robot body frame, and the `/tf_static` transforms place every sensor in it.
# `odom` is fixed to the ground, and the `/tf` transforms place `base` in it.
TF_STATIC_TOPIC = "/tf_static"
REFERENCE_FRAME_IDS = ["base", "odom"]

SYNC_COMPONENT = "hesai"

# The cameras and the lidars run at 10 Hz on independent clocks. A frame is at most half a
# frame interval away from a tick.
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
# Read as a string, not as a path, so that a URI such as `s3://my-bucket/grand_tour/`
# survives unchanged.
mcap_path = env.str("EXAMPLES_GRAND_TOUR_MCAP_PATH", "datasets/grand_tour/")

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
