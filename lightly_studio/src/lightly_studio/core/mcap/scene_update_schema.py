"""The ROS 2 message definition of `foxglove_msgs/msg/SceneUpdate` and per-class colours.

`SCENE_UPDATE_MSGDEF` is the text that an MCAP Schema record holds for a `ros2msg`
channel: the top-level type, then each nested type after a separator line. The
`foxglove_msgs` types are from the `foxglove_msgs` ROS 2 package 3.6.3 (MIT license):
https://github.com/foxglove/foxglove-sdk/tree/4df96f16b09379a67ceedd7dfbb37c6065c9e0ac/ros/src/foxglove_msgs/ros2
The `geometry_msgs` and `builtin_interfaces` types are from ROS 2. Comments and default
values are removed. They do not change the encoded messages.
"""

from __future__ import annotations

SCENE_UPDATE_SCHEMA_NAME = "foxglove_msgs/msg/SceneUpdate"

SCENE_UPDATE_MSGDEF = """foxglove_msgs/SceneEntityDeletion[] deletions
foxglove_msgs/SceneEntity[] entities
================================================================================
MSG: foxglove_msgs/SceneEntityDeletion
builtin_interfaces/Time timestamp
uint8 MATCHING_ID=0
uint8 ALL=1
uint8 type
string id
================================================================================
MSG: foxglove_msgs/SceneEntity
builtin_interfaces/Time timestamp
string frame_id
string id
builtin_interfaces/Duration lifetime
bool frame_locked
foxglove_msgs/KeyValuePair[] metadata
foxglove_msgs/ArrowPrimitive[] arrows
foxglove_msgs/CubePrimitive[] cubes
foxglove_msgs/SpherePrimitive[] spheres
foxglove_msgs/CylinderPrimitive[] cylinders
foxglove_msgs/LinePrimitive[] lines
foxglove_msgs/TriangleListPrimitive[] triangles
foxglove_msgs/TextPrimitive[] texts
foxglove_msgs/ModelPrimitive[] models
================================================================================
MSG: foxglove_msgs/KeyValuePair
string key
string value
================================================================================
MSG: foxglove_msgs/ArrowPrimitive
geometry_msgs/Pose pose
float64 shaft_length
float64 shaft_diameter
float64 head_length
float64 head_diameter
foxglove_msgs/Color color
================================================================================
MSG: foxglove_msgs/CubePrimitive
geometry_msgs/Pose pose
geometry_msgs/Vector3 size
foxglove_msgs/Color color
================================================================================
MSG: foxglove_msgs/SpherePrimitive
geometry_msgs/Pose pose
geometry_msgs/Vector3 size
foxglove_msgs/Color color
================================================================================
MSG: foxglove_msgs/CylinderPrimitive
geometry_msgs/Pose pose
geometry_msgs/Vector3 size
float64 bottom_scale
float64 top_scale
foxglove_msgs/Color color
================================================================================
MSG: foxglove_msgs/LinePrimitive
uint8 LINE_STRIP=0
uint8 LINE_LOOP=1
uint8 LINE_LIST=2
uint8 type
geometry_msgs/Pose pose
float64 thickness
bool scale_invariant
geometry_msgs/Point[] points
foxglove_msgs/Color color
foxglove_msgs/Color[] colors
uint32[] indices
================================================================================
MSG: foxglove_msgs/TriangleListPrimitive
geometry_msgs/Pose pose
geometry_msgs/Point[] points
foxglove_msgs/Color color
foxglove_msgs/Color[] colors
uint32[] indices
================================================================================
MSG: foxglove_msgs/TextPrimitive
geometry_msgs/Pose pose
bool billboard
float64 font_size
bool scale_invariant
foxglove_msgs/Color color
string text
================================================================================
MSG: foxglove_msgs/ModelPrimitive
geometry_msgs/Pose pose
geometry_msgs/Vector3 scale
foxglove_msgs/Color color
bool override_color
string url
string media_type
uint8[] data
================================================================================
MSG: foxglove_msgs/Color
float64 r
float64 g
float64 b
float64 a
================================================================================
MSG: geometry_msgs/Vector3
float64 x
float64 y
float64 z
================================================================================
MSG: builtin_interfaces/Duration
int32 sec
uint32 nanosec
================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec
================================================================================
MSG: geometry_msgs/Pose
Point position
Quaternion orientation
================================================================================
MSG: geometry_msgs/Point
float64 x
float64 y
float64 z
================================================================================
MSG: geometry_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w"""

_ALPHA = 0.4

_CLASS_COLORS = {
    "truck_bed": (1.0, 0.616, 0.0, _ALPHA),
    "person": (1.0, 0.22, 0.22, _ALPHA),
    "truck_cabin": (0.22, 0.533, 1.0, _ALPHA),
    "truck": (0.4, 0.8, 0.3, _ALPHA),
}

_DEFAULT_COLOR = (0.7, 0.7, 0.7, _ALPHA)


def class_color(class_name: str) -> tuple[float, float, float, float]:
    """Returns the cube colour (r, g, b, a) for an annotation class.

    Args:
        class_name: The annotation class, e.g. `truck_bed`.

    Returns:
        The RGBA colour, each in `[0, 1]`. Unknown classes get a neutral grey.
    """
    return _CLASS_COLORS.get(class_name, _DEFAULT_COLOR)
