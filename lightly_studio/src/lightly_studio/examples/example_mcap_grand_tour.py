"""Example of how to index a GrandTour mission into LightlyStudio.

The GrandTour dataset (https://grand-tour.leggedrobotics.com) holds missions of an ANYmal
legged robot with the Boxi sensor payload. The Hugging Face release
(https://huggingface.co/datasets/leggedrobotics/grand_tour_dataset) needs no registration.
It stores each mission as Zarr groups in `<mission>/data/` and as JPEG frames in
`<mission>/images/`, which an MCAP dataset cannot read. Convert one mission to a ros2 MCAP
file first:

    # Download `data/{tf,anymal_state_odometry,hdr_*}.tar`,
    # `data/{hesai,velodyne}_points_undistorted.tar` and `images/hdr_*.tar` of a mission,
    # for example `2024-11-02-21-12-51`, and extract them. Encode each HDR camera with PyAV
    # (libx264, a keyframe every 10 frames, no B-frames) and write the topics listed below.

The converted file has these topics:

    /hdr_{front,left,right}/compressed_video  foxglove_msgs/msg/CompressedVideo  H.264, 10 Hz
    /hdr_{front,left,right}/camera_info       sensor_msgs/msg/CameraInfo
    /hesai_points_undistorted                 sensor_msgs/msg/PointCloud2        10 Hz
    /velodyne_points_undistorted              sensor_msgs/msg/PointCloud2        10 Hz
    /tf_static                                tf2_msgs/msg/TFMessage
    /tf                                       tf2_msgs/msg/TFMessage             odom -> base

The images are 1920x1280. The Hesai XT-32 is on the Boxi payload, and the Velodyne VLP-16
is on the rear of the ANYmal body. The point clouds have the fields x, y, z and intensity.
The Zarr arrays are padded, so only the first `valid` points of each sweep are written. The
`/tf_static` edges come from `tf.attrs["tf"]`. GrandTour stores each edge as the transform
from the parent frame into the child frame, which is the inverse of a ROS transform, so
every edge is inverted. The `/tf` edges come from `anymal_state_odometry` without change.

One recording becomes one sequence of groups. Every Hesai point cloud is a tick, and the
Velodyne point cloud and the frame of each camera are paired to it.

Set `EXAMPLES_GRAND_TOUR_PATH` to the converted `.mcap` file, or to its folder, to run this.
"""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio.database import db_manager

COMPONENTS = [
    ls.McapComponentSpec(
        name=name,
        mcap_data_type=ls.McapDataType.VIDEO_FRAME,
        topic=f"/hdr_{name}/compressed_video",
        camera_info_topic=f"/hdr_{name}/camera_info",
    )
    for name in ["front", "left", "right"]
] + [
    ls.McapComponentSpec(
        name=name,
        mcap_data_type=ls.McapDataType.POINT_CLOUD,
        topic=f"/{name}_points_undistorted",
        frame_id=f"{name}_lidar",
    )
    for name in ["hesai", "velodyne"]
]

SYNC_COMPONENT = "hesai"

# The lidars and the cameras run at 10 Hz on independent clocks. A frame is at most half a
# frame interval away from a tick.
MAX_PAIRING_DIFF_NS = 50_000_000

# Frames in the viewer Frame menu. The first is the default. `base` is the robot body frame,
# and the `/tf_static` transforms place every sensor in it. `odom` is fixed to the ground,
# and the `/tf` transforms place `base` in it.
REFERENCE_FRAME_IDS = ["base", "odom"]

env = Env()
env.read_env()
grand_tour_path = env.str("EXAMPLES_GRAND_TOUR_PATH", r"D:\data\grand_tour\clips\mcap_velodyne")

db_manager.connect(cleanup_existing=True)
dataset = ls.McapDataset.load_or_create(components=COMPONENTS, name="grand_tour")
dataset.add_mcaps_from_path(
    path=grand_tour_path,
    sync_component=SYNC_COMPONENT,
    components=COMPONENTS,
    max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    reference_frame_ids=REFERENCE_FRAME_IDS,
)

for sequence in dataset.get_sequences():
    recording = dataset.get_recording(recording_id=sequence.recording_id)
    print(f"{len(sequence.get_samples())} groups indexed from {recording.uri}")

ls.start_gui()
