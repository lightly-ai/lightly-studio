"""Converts one GrandTour mission from the Hugging Face Zarr release to a `gt_box` MCAP file.

The official GrandTour MCAP files from https://grand-tour.leggedrobotics.com, for example
`day_street.mcap`, use the topic names, message types and frame ids of the Boxi sensor
payload. This script writes the same layout from the Hugging Face release
(https://huggingface.co/datasets/leggedrobotics/grand_tour_dataset), so that one example
indexes both:

    /gt_box/<camera>/image_raw/compressed  sensor_msgs/msg/CompressedImage  JPEG, 10 Hz
    /gt_box/<camera>/camera_info           sensor_msgs/msg/CameraInfo       one per image
    /gt_box/hesai/points                   sensor_msgs/msg/PointCloud2      10 Hz
    /gt_box/livox/lidar                    sensor_msgs/msg/PointCloud2      10 Hz
    /tf_static                             tf2_msgs/msg/TFMessage
    /tf                                    tf2_msgs/msg/TFMessage           odom -> base

The official files have only `hdr_front` and no transforms. The other cameras and the
transforms are extra topics, which an example uses when a file has them.

- Each image is the JPEG file of the release, without a new encoding. Its `format` is
  `rgb8; jpeg compressed bgr8`, as in the official files. The cameras default to
  `hdr_front`, `hdr_left` and `hdr_right`.
- Each point cloud has float32 x, y, z and intensity. The official point clouds also have
  per-point fields, e.g. `ring` and `timestamp`, which this script does not write. The Zarr
  arrays are padded to a fixed width. Only the first `valid` points are kept. The Hesai
  sets the time window when `--max-seconds` is not given.
- The frame ids come from the Zarr groups, e.g. `hdr_front`, `hesai_lidar` and
  `livox_lidar`.
- The log time and the header stamp of each message are its capture time. In the official
  files, the log time is the receive time, which is up to 100 ms later.
- `tf.attrs["tf"]` becomes `/tf_static`, with every edge inverted, because GrandTour
  stores the transform from the parent frame into the child frame. The tree is
  `base -> box_base -> <sensor>`. `anymal_state_odometry` becomes `/tf` with
  `odom -> base`. `--no-tf` leaves both out, as in the official files.

Usage:
    python grand_tour_to_gt_box_mcap.py <mission_dir> <output.mcap> \
        [--start-seconds 30] [--max-seconds 60] [--hesai hesai_points] [--livox livox_points]

`<mission_dir>` holds `data/` (with the camera and the lidar groups, and `tf` and
`anymal_state_odometry` without `--no-tf`) and `images/` (one JPEG folder per camera). The raw
lidar groups `hesai_points` and `livox_points` match the official files, and
`download_grand_tour_clips.py` downloads them. Other groups also work, e.g.
`--hesai hesai_points_undistorted --livox ""` for a mission without a Livox group.

Requires `zarr<3`, `numcodecs`, `numpy`, `pillow`, `mcap`, `mcap-ros2-support` and
`scipy`.
"""

from __future__ import annotations

import argparse
import heapq
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from mcap.records import Schema
from mcap_ros2.writer import Writer
from PIL import Image
from scipy.spatial.transform import Rotation

_HEADER_MSGDEF = """
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
"""

_COMPRESSED_IMAGE_MSGDEF = (
    """
std_msgs/Header header
string format
uint8[] data
"""
    + _HEADER_MSGDEF
)

_CAMERA_INFO_MSGDEF = (
    """
std_msgs/Header header
uint32 height
uint32 width
string distortion_model
float64[] d
float64[9] k
float64[9] r
float64[12] p
uint32 binning_x
uint32 binning_y
sensor_msgs/RegionOfInterest roi
"""
    + _HEADER_MSGDEF
    + """
================================================================================
MSG: sensor_msgs/RegionOfInterest
uint32 x_offset
uint32 y_offset
uint32 height
uint32 width
bool do_rectify
"""
)

_POINT_CLOUD_MSGDEF = (
    """
std_msgs/Header header
uint32 height
uint32 width
sensor_msgs/PointField[] fields
bool is_bigendian
uint32 point_step
uint32 row_step
uint8[] data
bool is_dense
"""
    + _HEADER_MSGDEF
    + """
================================================================================
MSG: sensor_msgs/PointField
string name
uint32 offset
uint8 datatype
uint32 count
"""
)

_TF_MESSAGE_MSGDEF = (
    """
geometry_msgs/TransformStamped[] transforms
================================================================================
MSG: geometry_msgs/TransformStamped
std_msgs/Header header
string child_frame_id
geometry_msgs/Transform transform
================================================================================
MSG: geometry_msgs/Transform
geometry_msgs/Vector3 translation
geometry_msgs/Quaternion rotation
================================================================================
MSG: geometry_msgs/Vector3
float64 x
float64 y
float64 z
================================================================================
MSG: geometry_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w
"""
    + _HEADER_MSGDEF
)

# The topics of the official files. The Hesai is first, so it sets the time window.
_HESAI_TOPIC = "/gt_box/hesai/points"
_LIVOX_TOPIC = "/gt_box/livox/lidar"
_IMAGE_FORMAT = "rgb8; jpeg compressed bgr8"

_FLOAT32 = 7
_POINT_FIELDS = ("x", "y", "z", "intensity")

# Event kinds, in the order they are written when two events share a timestamp.
_TF, _LIDAR, _CAMERA = 0, 1, 2


def main() -> None:
    """Parses the command line and converts the mission."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("mission_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--cameras",
        default="hdr_front,hdr_left,hdr_right",
        help="Comma-separated camera groups.",
    )
    parser.add_argument("--hesai", default="hesai_points", help="The Hesai group.")
    parser.add_argument("--livox", default="livox_points", help="The Livox group, '' for none.")
    parser.add_argument("--start-seconds", type=float, default=0.0, help="Skip the first N s.")
    parser.add_argument("--max-seconds", type=float, default=None, help="Only convert N s.")
    parser.add_argument(
        "--tf",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write /tf_static and /tf. --no-tf leaves them out.",
    )
    args = parser.parse_args()

    lidar_topics = {_HESAI_TOPIC: args.hesai, _LIVOX_TOPIC: args.livox}
    convert(
        mission_dir=args.mission_dir,
        output=args.output,
        cameras=[name for name in args.cameras.split(",") if name],
        lidars={group: topic for topic, group in lidar_topics.items() if group},
        start_seconds=args.start_seconds,
        max_seconds=args.max_seconds,
        with_tf=args.tf,
    )


def convert(  # noqa: PLR0913
    mission_dir: Path,
    output: Path,
    cameras: list[str],
    lidars: dict[str, str],
    start_seconds: float,
    max_seconds: float | None,
    with_tf: bool,
) -> None:
    """Writes the cameras and the lidars of a mission to an MCAP file.

    Args:
        mission_dir: The mission folder with `data/` and `images/`.
        output: The MCAP file to write.
        cameras: The camera groups, e.g. `hdr_front`.
        lidars: The topic of each lidar group. The first lidar sets the time window when
            `max_seconds` is not given.
        start_seconds: The seconds to skip after the first stamp of all sensors.
        max_seconds: The seconds to convert, or `None` for all sweeps of the first lidar.
        with_tf: Whether to write `/tf_static` and `/tf`.
    """
    if not lidars:
        raise ValueError("Give at least one lidar group.")
    root = zarr.open_group(str(mission_dir / "data"), mode="r")
    camera_stamps = {camera: _stamps_ns(root[camera]["timestamp"][:]) for camera in cameras}
    lidar_stamps = {lidar: _stamps_ns(root[lidar]["timestamp"][:]) for lidar in lidars}

    first_stamps = [int(stamps[0]) for stamps in [*lidar_stamps.values(), *camera_stamps.values()]]
    start_ns = max(first_stamps) + int(start_seconds * 1e9)
    first_lidar_stamps = next(iter(lidar_stamps.values()))
    end_ns = (
        int(first_lidar_stamps[-1]) if max_seconds is None else start_ns + int(max_seconds * 1e9)
    )

    stamps_by_source = {
        **{(_LIDAR, lidar): stamps for lidar, stamps in lidar_stamps.items()},
        **{(_CAMERA, camera): stamps for camera, stamps in camera_stamps.items()},
    }
    if with_tf:
        stamps_by_source[(_TF, "odom")] = _stamps_ns(root["anymal_state_odometry"]["timestamp"][:])
    events = [
        [(int(t), kind, name, i) for i, t in enumerate(stamps) if start_ns <= t <= end_ns]
        for (kind, name), stamps in stamps_by_source.items()
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    counts = {_TF: 0, _LIDAR: 0, _CAMERA: 0}
    with output.open("wb") as stream:
        writer = Writer(stream)
        image_schema = writer.register_msgdef(
            "sensor_msgs/msg/CompressedImage", _COMPRESSED_IMAGE_MSGDEF
        )
        camera_info_schema = writer.register_msgdef(
            "sensor_msgs/msg/CameraInfo", _CAMERA_INFO_MSGDEF
        )
        point_cloud_schema = writer.register_msgdef(
            "sensor_msgs/msg/PointCloud2", _POINT_CLOUD_MSGDEF
        )
        tf_schema = writer.register_msgdef("tf2_msgs/msg/TFMessage", _TF_MESSAGE_MSGDEF)

        if with_tf:
            writer.write_message(
                topic="/tf_static",
                schema=tf_schema,
                message={"transforms": _static_transforms(root["tf"].attrs["tf"], start_ns)},
                log_time=start_ns,
                publish_time=start_ns,
            )
            odometry = root["anymal_state_odometry"]
            odometry_positions = odometry["pose_pos"][:]
            odometry_orientations = odometry["pose_orien"][:]

        camera_attrs = {camera: dict(root[camera].attrs) for camera in cameras}
        for camera in cameras:
            # A clip holds only the images of its time window, so read the first of them.
            first_index = int(np.searchsorted(camera_stamps[camera], start_ns))
            _check_image_size(
                camera=camera,
                info=camera_attrs[camera]["camera_info"],
                image_path=_image_path(mission_dir, camera, first_index),
            )

        lidar_readers = {lidar: _LidarReader(group=root[lidar]) for lidar in lidars}

        for stamp_ns, kind, name, index in heapq.merge(*events):
            if kind == _TF:
                message = {
                    "transforms": [
                        _transform_stamped(
                            parent="odom",
                            child="base",
                            translation=odometry_positions[index],
                            rotation_xyzw=odometry_orientations[index],
                            stamp_ns=stamp_ns,
                        )
                    ]
                }
                writer.write_message(
                    topic="/tf",
                    schema=tf_schema,
                    message=message,
                    log_time=stamp_ns,
                    publish_time=stamp_ns,
                )
            elif kind == _LIDAR:
                reader = lidar_readers[name]
                xyz, intensity = reader.get(index)
                writer.write_message(
                    topic=lidars[name],
                    schema=point_cloud_schema,
                    message=_point_cloud_message(
                        xyz=xyz, intensity=intensity, frame_id=reader.frame_id, stamp_ns=stamp_ns
                    ),
                    log_time=stamp_ns,
                    publish_time=stamp_ns,
                )
            else:
                _write_image(
                    writer=writer,
                    image_schema=image_schema,
                    camera_info_schema=camera_info_schema,
                    camera=name,
                    attrs=camera_attrs[name],
                    image_path=_image_path(mission_dir, name, index),
                    stamp_ns=stamp_ns,
                )
            counts[kind] += 1
            if sum(counts.values()) % 2000 == 0:
                seconds = (stamp_ns - start_ns) / 1e9
                print(
                    f"{seconds:7.1f} s: {counts[_LIDAR]} sweeps, {counts[_CAMERA]} images, "
                    f"{counts[_TF]} poses"
                )
        writer.finish()

    print(
        f"Wrote {output}: {counts[_LIDAR]} sweeps, {counts[_CAMERA]} images, {counts[_TF]} poses, "
        f"{(end_ns - start_ns) / 1e9:.1f} s, {output.stat().st_size / 1e9:.2f} GB"
    )


class _LidarReader:
    """Reads the valid points of one sweep of a lidar group."""

    def __init__(self, group: zarr.Group) -> None:
        self.frame_id: str = group.attrs["frame_id"]
        self._points = _BlockReader(group["points"])
        self._intensity = _BlockReader(group["intensity"])
        self._valid = group["valid"][:, 0]

    def get(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        count = int(self._valid[index])
        return self._points.get(index)[:count], self._intensity.get(index)[:count]


class _BlockReader:
    """Reads a Zarr array one chunk of rows at a time, so each chunk is decompressed once."""

    def __init__(self, array: zarr.Array) -> None:
        self._array = array
        self._rows = array.chunks[0]
        self._start = -1
        self._block: np.ndarray | None = None

    def get(self, index: int) -> np.ndarray:
        start = index - index % self._rows
        if start != self._start or self._block is None:
            self._block = self._array[start : start + self._rows]
            self._start = start
        return self._block[index - start]


def _write_image(  # noqa: PLR0913
    writer: Writer,
    image_schema: Schema,
    camera_info_schema: Schema,
    camera: str,
    attrs: dict[str, Any],
    image_path: Path,
    stamp_ns: int,
) -> None:
    """Writes the JPEG file of one image and its camera info, as the official files do."""
    header = {"stamp": _time(stamp_ns), "frame_id": attrs["frame_id"]}
    writer.write_message(
        topic=f"/gt_box/{camera}/image_raw/compressed",
        schema=image_schema,
        message={"header": header, "format": _IMAGE_FORMAT, "data": image_path.read_bytes()},
        log_time=stamp_ns,
        publish_time=stamp_ns,
    )
    writer.write_message(
        topic=f"/gt_box/{camera}/camera_info",
        schema=camera_info_schema,
        message=_camera_info_message(
            info=attrs["camera_info"], frame_id=attrs["frame_id"], stamp_ns=stamp_ns
        ),
        log_time=stamp_ns,
        publish_time=stamp_ns,
    )


def _check_image_size(camera: str, info: dict[str, Any], image_path: Path) -> None:
    """Prints a warning when the camera info size differs from the image size."""
    width, height = Image.open(image_path).size
    if (info["width"], info["height"]) != (width, height):
        print(
            f"{camera}: camera_info is {info['width']}x{info['height']}, "
            f"the images are {width}x{height}"
        )


def _stamps_ns(seconds: np.ndarray) -> np.ndarray:
    return np.round(seconds.astype(np.float64) * 1e9).astype(np.int64)


def _image_path(mission_dir: Path, camera: str, index: int) -> Path:
    return mission_dir / "images" / camera / f"{index:06d}.jpeg"


def _static_transforms(edges: dict[str, dict[str, Any]], stamp_ns: int) -> list[dict[str, Any]]:
    transforms = []
    for edge in edges.values():
        translation = edge["translation"]
        rotation = edge["rotation"]
        # GrandTour stores the transform from the parent into the child frame. Invert it.
        inverse = Rotation.from_quat(
            [rotation["x"], rotation["y"], rotation["z"], rotation["w"]]
        ).inv()
        inverse_translation = -inverse.apply([translation["x"], translation["y"], translation["z"]])
        transforms.append(
            _transform_stamped(
                parent=edge["base_frame_id"],
                child=edge["child_frame_id"],
                translation=inverse_translation,
                rotation_xyzw=inverse.as_quat(),
                stamp_ns=stamp_ns,
            )
        )
    return transforms


def _transform_stamped(
    parent: str, child: str, translation: np.ndarray, rotation_xyzw: np.ndarray, stamp_ns: int
) -> dict[str, Any]:
    x, y, z = (float(value) for value in translation)
    qx, qy, qz, qw = (float(value) for value in rotation_xyzw)
    return {
        "header": {"stamp": _time(stamp_ns), "frame_id": parent},
        "child_frame_id": child,
        "transform": {
            "translation": {"x": x, "y": y, "z": z},
            "rotation": {"x": qx, "y": qy, "z": qz, "w": qw},
        },
    }


def _camera_info_message(info: dict[str, Any], frame_id: str, stamp_ns: int) -> dict[str, Any]:
    roi = info["roi"]
    return {
        "header": {"stamp": _time(stamp_ns), "frame_id": frame_id},
        "height": int(info["height"]),
        "width": int(info["width"]),
        "distortion_model": info["distortion_model"],
        "d": [float(value) for value in info["D"]],
        "k": [float(value) for value in info["K"]],
        "r": [float(value) for value in info["R"]],
        "p": [float(value) for value in info["P"]],
        "binning_x": int(info["binning_x"]),
        "binning_y": int(info["binning_y"]),
        "roi": {
            "x_offset": int(roi["x_offset"]),
            "y_offset": int(roi["y_offset"]),
            "height": int(roi["height"]),
            "width": int(roi["width"]),
            "do_rectify": bool(roi["do_rectify"]),
        },
    }


def _point_cloud_message(
    xyz: np.ndarray, intensity: np.ndarray, frame_id: str, stamp_ns: int
) -> dict[str, Any]:
    packed = np.empty((len(xyz), len(_POINT_FIELDS)), dtype="<f4")
    packed[:, :3] = xyz
    packed[:, 3] = intensity
    point_step = packed.itemsize * len(_POINT_FIELDS)
    return {
        "header": {"stamp": _time(stamp_ns), "frame_id": frame_id},
        "height": 1,
        "width": len(packed),
        "fields": [
            {"name": name, "offset": index * packed.itemsize, "datatype": _FLOAT32, "count": 1}
            for index, name in enumerate(_POINT_FIELDS)
        ],
        "is_bigendian": False,
        "point_step": point_step,
        "row_step": point_step * len(packed),
        "data": packed.tobytes(),
        "is_dense": bool(np.isfinite(packed).all()),
    }


def _time(stamp_ns: int) -> dict[str, int]:
    return {"sec": stamp_ns // 1_000_000_000, "nanosec": stamp_ns % 1_000_000_000}


if __name__ == "__main__":
    main()
