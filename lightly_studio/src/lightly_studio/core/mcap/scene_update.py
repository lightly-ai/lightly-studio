"""Reading cuboids and frame tags from decoded SceneUpdate messages."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from lightly_studio.core.mcap import capture_time, message_fields
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.type_definitions import CuboidLabel, FrameTags, SceneUpdateLabels

FRAME_ENTITY_ID = "frame"

_ENTITIES_FIELDS = ("entities",)
_ID_FIELDS = ("id",)
_TIMESTAMP_FIELDS = ("timestamp",)
_FRAME_ID_FIELDS = ("frame_id",)
_METADATA_FIELDS = ("metadata",)
_CUBES_FIELDS = ("cubes",)
_POSE_FIELDS = ("pose",)
_POSITION_FIELDS = ("position",)
_ORIENTATION_FIELDS = ("orientation",)
_SIZE_FIELDS = ("size",)
_KEY_FIELDS = ("key",)
_VALUE_FIELDS = ("value",)
_SEC_FIELDS = ("sec", "seconds")
_NSEC_FIELDS = ("nsec", "nanosec", "nanoseconds")

_CLASS_KEY = "class"
_TRACK_ID_KEY = "track_id"
_PARENT_TRACK_ID_KEY = "parent_track_id"
_INTERPOLATED_KEY = "interpolated"
_NOTE_KEY = "note"


def from_decoded_message(decoded_message: Any) -> SceneUpdateLabels:
    """Extracts cuboids and frame tags from a decoded SceneUpdate message.

    Reads `foxglove_msgs/msg/SceneUpdate` and JSON dicts that use the same field
    names. `deletions` are ignored. An entity whose `id` is `frame` is tags, not
    a box.

    Args:
        decoded_message: A decoded SceneUpdate message.

    Returns:
        The cuboids and optional frame tags of the message.

    Raises:
        McapAccessError: If an entity is missing required fields, or if a cuboid
            has a non-positive size or a zero quaternion.
    """
    entities = message_fields.get_field(decoded_message, _ENTITIES_FIELDS) or ()
    cuboids: list[CuboidLabel] = []
    frame_tags: FrameTags | None = None
    for entity in entities:
        if _entity_id(entity) == FRAME_ENTITY_ID:
            if frame_tags is not None:
                raise McapAccessError("SceneUpdate has multiple frame entities.")
            frame_tags = _frame_tags(entity)
            continue
        cuboids.append(_cuboid(entity))
    return SceneUpdateLabels(cuboids=tuple(cuboids), frame_tags=frame_tags)


def _cuboid(entity: Any) -> CuboidLabel:
    """Returns the cuboid described by a SceneEntity."""
    metadata = _metadata_map(entity)
    cube = _first_cube(entity)
    pose = message_fields.require_field(cube, _POSE_FIELDS)
    position = _xyz(message_fields.require_field(pose, _POSITION_FIELDS))
    rotation = _quaternion(message_fields.require_field(pose, _ORIENTATION_FIELDS))
    size = _xyz(message_fields.require_field(cube, _SIZE_FIELDS))
    if not all(math.isfinite(value) for value in (*position, *rotation, *size)):
        raise McapAccessError("Cuboid pose and size must be finite.")
    if any(extent <= 0 for extent in size):
        raise McapAccessError("Cuboid size must be positive.")
    return CuboidLabel(
        timestamp_ns=_timestamp_ns(message_fields.require_field(entity, _TIMESTAMP_FIELDS)),
        frame_id=str(message_fields.require_field(entity, _FRAME_ID_FIELDS)),
        class_name=_require_metadata(metadata, _CLASS_KEY),
        track_id=_parse_int(_require_metadata(metadata, _TRACK_ID_KEY), _TRACK_ID_KEY),
        parent_track_id=_optional_int(metadata.get(_PARENT_TRACK_ID_KEY)),
        interpolated=_parse_bool(metadata.get(_INTERPOLATED_KEY)),
        position=position,
        rotation=rotation,
        size=size,
    )


def _frame_tags(entity: Any) -> FrameTags:
    """Returns the frame-level tags of the metadata-only `frame` entity."""
    metadata = _metadata_map(entity)
    note = metadata.pop(_NOTE_KEY, None)
    tags = tuple(sorted(key for key, value in metadata.items() if _parse_bool(value, key)))
    return FrameTags(
        timestamp_ns=_timestamp_ns(message_fields.require_field(entity, _TIMESTAMP_FIELDS)),
        tags=tags,
        note=None if note is None or str(note) == "" else str(note),
    )


def _entity_id(entity: Any) -> str:
    """Returns the SceneEntity id."""
    return str(message_fields.require_field(entity, _ID_FIELDS))


def _first_cube(entity: Any) -> Any:
    """Returns the only CubePrimitive of a SceneEntity."""
    cubes = message_fields.get_field(entity, _CUBES_FIELDS) or ()
    if not cubes:
        raise McapAccessError("SceneEntity has no cube primitive.")
    if len(cubes) > 1:
        raise McapAccessError("SceneEntity has multiple cube primitives.")
    return cubes[0]


def _metadata_map(entity: Any) -> dict[str, str]:
    """Returns SceneEntity metadata as a key-to-value map."""
    entries = message_fields.get_field(entity, _METADATA_FIELDS) or ()
    if isinstance(entries, Mapping):
        return {str(key): str(value) for key, value in entries.items()}
    result: dict[str, str] = {}
    for entry in entries:
        key = message_fields.get_field(entry, _KEY_FIELDS)
        value = message_fields.get_field(entry, _VALUE_FIELDS)
        if key is None or value is None:
            continue
        result[str(key)] = str(value)
    return result


def _require_metadata(metadata: Mapping[str, str], key: str) -> str:
    """Returns a required metadata value."""
    value = metadata.get(key)
    if value is None or value == "":
        raise McapAccessError(f"SceneEntity metadata is missing '{key}'.")
    return value


def _optional_int(value: str | None) -> int | None:
    """Parses an optional integer metadata value."""
    if value is None or value == "":
        return None
    return _parse_int(value, _PARENT_TRACK_ID_KEY)


def _parse_int(value: str, key: str) -> int:
    """Parses an integer metadata value."""
    try:
        return int(value)
    except ValueError as error:
        raise McapAccessError(f"SceneEntity metadata '{key}' is not an integer.") from error


def _parse_bool(value: str | None, key: str = _INTERPOLATED_KEY) -> bool:
    """Parses a boolean metadata value. Missing or empty is false."""
    if value is None or value == "":
        return False
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise McapAccessError(f"SceneEntity metadata '{key}' must be true or false.")


def _timestamp_ns(timestamp: Any) -> int:
    """Returns a Time message as nanoseconds since the Unix epoch."""
    sec = int(message_fields.require_field(timestamp, _SEC_FIELDS))
    nsec = message_fields.get_field(timestamp, _NSEC_FIELDS)
    return sec * capture_time.NANOSECONDS_PER_SECOND + (0 if nsec is None else int(nsec))


def _xyz(vector: Any) -> tuple[float, float, float]:
    """Returns an (x, y, z) triple from a vector message."""
    return (
        float(message_fields.require_field(vector, ("x",))),
        float(message_fields.require_field(vector, ("y",))),
        float(message_fields.require_field(vector, ("z",))),
    )


def _quaternion(orientation: Any) -> tuple[float, float, float, float]:
    """Returns an (x, y, z, w) quaternion. Rejects the zero quaternion."""
    quaternion = (
        float(message_fields.require_field(orientation, ("x",))),
        float(message_fields.require_field(orientation, ("y",))),
        float(message_fields.require_field(orientation, ("z",))),
        float(message_fields.require_field(orientation, ("w",))),
    )
    if quaternion == (0.0, 0.0, 0.0, 0.0):
        raise McapAccessError("Cuboid quaternion must be non-zero.")
    return quaternion
