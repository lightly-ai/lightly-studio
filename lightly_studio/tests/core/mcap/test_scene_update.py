from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lightly_studio.core.mcap import scene_update
from lightly_studio.core.mcap.errors import McapAccessError

TIMESTAMP_NS = 1_723_712_400_100_000_000


def _time(sec: int = 1723712400, nsec: int = 100_000_000) -> Any:
    return SimpleNamespace(sec=sec, nsec=nsec)


def _vector(x: float, y: float, z: float) -> Any:
    return SimpleNamespace(x=x, y=y, z=z)


def _quat(x: float = 0.0043, y: float = 0.0512, z: float = 0.7071, w: float = 0.7052) -> Any:
    return SimpleNamespace(x=x, y=y, z=z, w=w)


def _metadata(items: dict[str, str]) -> list[Any]:
    return [SimpleNamespace(key=key, value=value) for key, value in items.items()]


def _cube(
    position: tuple[float, float, float] = (12.41, -3.08, 1.62),
    size: tuple[float, float, float] = (5.20, 2.44, 1.15),
    orientation: Any | None = None,
) -> Any:
    return SimpleNamespace(
        pose=SimpleNamespace(
            position=_vector(*position),
            orientation=_quat() if orientation is None else orientation,
        ),
        size=_vector(*size),
    )


def _entity(
    entity_id: str,
    metadata: dict[str, str],
    cubes: list[Any] | None = None,
    timestamp: Any | None = None,
    frame_id: str = "odom",
) -> Any:
    return SimpleNamespace(
        timestamp=_time() if timestamp is None else timestamp,
        frame_id=frame_id,
        id=entity_id,
        metadata=_metadata(metadata),
        cubes=[] if cubes is None else cubes,
    )


def test_from_decoded_message__nested_truck() -> None:
    message = SimpleNamespace(
        entities=[
            _entity(
                "truck_3",
                {
                    "class": "truck",
                    "track_id": "3",
                    "parent_track_id": "",
                    "interpolated": "false",
                },
                cubes=[_cube()],
            ),
            _entity(
                "truck_cabin_5",
                {
                    "class": "truck_cabin",
                    "track_id": "5",
                    "parent_track_id": "3",
                    "interpolated": "false",
                },
                cubes=[_cube(position=(11.0, -3.08, 1.62), size=(2.0, 2.0, 1.8))],
            ),
            _entity(
                "truck_bed_7",
                {
                    "class": "truck_bed",
                    "track_id": "7",
                    "parent_track_id": "3",
                    "interpolated": "true",
                },
                cubes=[_cube(size=(5.20, 2.44, 1.15))],
            ),
        ]
    )

    labels = scene_update.from_decoded_message(message)

    assert labels.frame_tags is None
    assert len(labels.cuboids) == 3
    truck, cabin, bed = labels.cuboids
    assert truck.class_name == "truck"
    assert truck.track_id == 3
    assert truck.parent_track_id is None
    assert truck.interpolated is False
    assert truck.timestamp_ns == TIMESTAMP_NS
    assert truck.frame_id == "odom"
    assert truck.position == pytest.approx((12.41, -3.08, 1.62))
    assert truck.size == pytest.approx((5.20, 2.44, 1.15))
    assert cabin.parent_track_id == 3
    assert bed.track_id == 7
    assert bed.interpolated is True


def test_from_decoded_message__json() -> None:
    message = {
        "entities": [
            {
                "timestamp": {"sec": 1723712400, "nsec": 100000000},
                "frame_id": "odom",
                "id": "person_1",
                "metadata": [
                    {"key": "class", "value": "person"},
                    {"key": "track_id", "value": "1"},
                ],
                "cubes": [
                    {
                        "pose": {
                            "position": {"x": 1.0, "y": 2.0, "z": 0.9},
                            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                        },
                        "size": {"x": 0.6, "y": 0.6, "z": 1.8},
                    }
                ],
            }
        ]
    }

    labels = scene_update.from_decoded_message(message)

    person = labels.cuboids[0]
    assert person.class_name == "person"
    assert person.track_id == 1
    assert person.parent_track_id is None
    assert person.rotation == (0.0, 0.0, 0.0, 1.0)


def test_from_decoded_message__empty_scene() -> None:
    labels = scene_update.from_decoded_message({"entities": []})

    assert labels.cuboids == ()
    assert labels.frame_tags is None


def test_from_decoded_message__frame_tags() -> None:
    message = SimpleNamespace(
        entities=[
            _entity(
                "frame",
                {"lidar_dropout": "true", "note": "sparse returns"},
                cubes=[],
            )
        ]
    )

    labels = scene_update.from_decoded_message(message)

    assert labels.cuboids == ()
    assert labels.frame_tags is not None
    assert labels.frame_tags.timestamp_ns == TIMESTAMP_NS
    assert labels.frame_tags.tags == ("lidar_dropout",)
    assert labels.frame_tags.note == "sparse returns"


def test_from_decoded_message__false_frame_tag() -> None:
    message = SimpleNamespace(
        entities=[
            _entity(
                "frame",
                {"lidar_dropout": "false", "camera_dropout": "true"},
            )
        ]
    )

    labels = scene_update.from_decoded_message(message)

    assert labels.frame_tags is not None
    assert labels.frame_tags.tags == ("camera_dropout",)


def test_from_decoded_message__multiple_frame_entities() -> None:
    message = SimpleNamespace(
        entities=[
            _entity("frame", {"lidar_dropout": "true"}),
            _entity("frame", {"camera_dropout": "true"}),
        ]
    )

    with pytest.raises(McapAccessError, match="multiple frame entities"):
        scene_update.from_decoded_message(message)


def test_from_decoded_message__multiple_cubes() -> None:
    entity = _entity(
        "truck_3",
        {"class": "truck", "track_id": "3"},
        cubes=[_cube(), _cube()],
    )

    with pytest.raises(McapAccessError, match="multiple cube primitives"):
        scene_update.from_decoded_message(SimpleNamespace(entities=[entity]))


def test_from_decoded_message__missing_class() -> None:
    entity = _entity("truck_3", {"track_id": "3"}, cubes=[_cube()])

    with pytest.raises(McapAccessError, match="missing 'class'"):
        scene_update.from_decoded_message(SimpleNamespace(entities=[entity]))


def test_from_decoded_message__zero_quaternion() -> None:
    entity = _entity(
        "truck_3",
        {"class": "truck", "track_id": "3"},
        cubes=[_cube(orientation=_quat(0.0, 0.0, 0.0, 0.0))],
    )

    with pytest.raises(McapAccessError, match="quaternion must be non-zero"):
        scene_update.from_decoded_message(SimpleNamespace(entities=[entity]))


def test_from_decoded_message__non_positive_size() -> None:
    entity = _entity(
        "truck_3",
        {"class": "truck", "track_id": "3"},
        cubes=[_cube(size=(0.0, 2.44, 1.15))],
    )

    with pytest.raises(McapAccessError, match="size must be positive"):
        scene_update.from_decoded_message(SimpleNamespace(entities=[entity]))


@pytest.mark.parametrize(
    ("position", "size"),
    [
        ((float("nan"), 0.0, 0.0), (1.0, 1.0, 1.0)),
        ((float("inf"), 0.0, 0.0), (1.0, 1.0, 1.0)),
        ((0.0, 0.0, 0.0), (float("nan"), 1.0, 1.0)),
        ((0.0, 0.0, 0.0), (float("inf"), 1.0, 1.0)),
    ],
)
def test_from_decoded_message__non_finite_cuboid(
    position: tuple[float, float, float],
    size: tuple[float, float, float],
) -> None:
    entity = _entity(
        "truck_3",
        {"class": "truck", "track_id": "3"},
        cubes=[_cube(position=position, size=size)],
    )

    with pytest.raises(McapAccessError, match="pose and size must be finite"):
        scene_update.from_decoded_message(SimpleNamespace(entities=[entity]))
