from __future__ import annotations

import math
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.cuboid_interpolation import CuboidInterpolationRange
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.dynamic_transform import DynamicTransformCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    dynamic_transform_resolver,
    sequence_resolver,
)
from lightly_studio.services import object_track_service
from lightly_studio.services.recording_service import world_poses
from tests.helpers_resolvers import create_annotation_label
from tests.services.object_track_service import helpers


def test_interpolate_cuboids__fills_gaps(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(
        session=db_session, scene=scene, timestamps=list(range(0, 10_000, 100))
    )
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    for seq_number in (3, 30, 50):
        helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[seq_number], track=track)

    _interpolate(session=db_session, ticks=ticks, track=track)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    filled = [*range(4, 30), *range(31, 50)]
    for seq_number in filled:
        cuboids = by_tick[ticks[seq_number]]
        assert len(cuboids) == 1
        details = cuboids[0].cuboid_3d_details
        assert details is not None
        assert details.interpolated is True
        assert details.frame_id == "odom"
        assert cuboids[0].annotation_label_id == scene.label_id
        assert cuboids[0].annotation_collection_id == by_tick[ticks[3]][0].annotation_collection_id
    for seq_number in [*range(3), *range(51, 100)]:
        assert ticks[seq_number] not in by_tick


def test_interpolate_cuboids__geometry_uses_timestamps(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 100])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, px=0.0)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[2], track=track, px=100.0)

    _interpolate(session=db_session, ticks=ticks, track=track)

    details = helpers.cuboids_by_tick(session=db_session, track=track)[ticks[1]][
        0
    ].cuboid_3d_details
    assert details is not None
    assert details.px == pytest.approx(10.0)


def test_interpolate_cuboids__replaces_interpolated_cuboids_between_anchors(
    db_session: Session,
) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20, 30, 40])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, px=0.0)
    copy_ids = [
        helpers.add_cuboid(
            session=db_session,
            scene=scene,
            tick_id=ticks[seq_number],
            track=track,
            px=0.0,
            interpolated=True,
        )
        for seq_number in (1, 2, 3)
    ]
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[4], track=track, px=40.0)

    _interpolate(session=db_session, ticks=ticks, track=track)

    for copy_id in copy_ids:
        assert annotation_resolver.get_by_id(session=db_session, annotation_id=copy_id) is None
    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    for seq_number, px in ((1, 10.0), (2, 20.0), (3, 30.0)):
        cuboids = by_tick[ticks[seq_number]]
        assert len(cuboids) == 1
        assert helpers.px_of(annotation=cuboids[0]) == pytest.approx(px)
        details = cuboids[0].cuboid_3d_details
        assert details is not None
        assert details.interpolated is True


def test_interpolate_cuboids__interpolated_cuboids_are_not_anchors(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[0], track=track, px=5.0, interpolated=True
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[2], track=track, px=7.0)

    _interpolate(session=db_session, ticks=ticks, track=track)

    assert ticks[1] not in helpers.cuboids_by_tick(session=db_session, track=track)


def test_interpolate_cuboids__keeps_cuboids_outside_anchor_pairs(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20, 30, 40])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    before_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[0], track=track, px=5.0, interpolated=True
    )
    start_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[1], track=track, px=7.0
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[3], track=track, px=9.0)
    after_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[4], track=track, px=6.0, interpolated=True
    )

    _interpolate(session=db_session, ticks=ticks, track=track)

    for annotation_id, px, interpolated in (
        (before_id, 5.0, True),
        (start_id, 7.0, False),
        (after_id, 6.0, True),
    ):
        annotation = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id)
        assert annotation is not None
        assert annotation.cuboid_3d_details is not None
        assert annotation.cuboid_3d_details.px == px
        assert annotation.cuboid_3d_details.interpolated is interpolated


def test_interpolate_cuboids__skips_frame_id_mismatch(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20, 30, 40])
    track = helpers.create_track(session=db_session, scene=scene, number=7)
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[0], track=track, frame_id="odom"
    )
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[2], track=track, frame_id="map"
    )
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[4], track=track, frame_id="map"
    )

    _interpolate(session=db_session, ticks=ticks, track=track)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    assert ticks[1] not in by_tick
    assert len(by_tick[ticks[3]]) == 1


def test_interpolate_cuboids__skips_class_mismatch(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    other_label = create_annotation_label(
        session=db_session, root_collection_id=scene.sequence_collection_id, label_name="truck"
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track)
    helpers.add_cuboid(
        session=db_session,
        scene=scene,
        tick_id=ticks[2],
        track=track,
        label_id=other_label.annotation_label_id,
    )

    _interpolate(session=db_session, ticks=ticks, track=track)

    assert ticks[1] not in helpers.cuboids_by_tick(session=db_session, track=track)


def test_interpolate_cuboids__range_replaces_only_selected_ticks(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(
        session=db_session, scene=scene, timestamps=list(range(0, 110, 10))
    )
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, px=0.0)
    copy_ids = {
        seq_number: helpers.add_cuboid(
            session=db_session,
            scene=scene,
            tick_id=ticks[seq_number],
            track=track,
            px=0.0,
            interpolated=True,
        )
        for seq_number in range(1, 10)
    }
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[10], track=track, px=100.0)

    _interpolate(session=db_session, ticks=ticks, track=track, start=3, end=5)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    for seq_number, px in ((3, 30.0), (4, 40.0), (5, 50.0)):
        assert len(by_tick[ticks[seq_number]]) == 1
        assert helpers.px_of(annotation=by_tick[ticks[seq_number]][0]) == pytest.approx(px)
    for seq_number in (1, 2, 6, 7, 8, 9):
        (cuboid,) = by_tick[ticks[seq_number]]
        assert cuboid.sample_id == copy_ids[seq_number]
        assert helpers.px_of(annotation=cuboid) == 0.0


def test_interpolate_cuboids__range_ignores_other_sources(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20, 30, 40])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, source="gt")
    pred_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[2], track=track, source="pred"
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[4], track=track, source="gt")

    _interpolate(session=db_session, ticks=ticks, track=track)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    assert len(by_tick[ticks[1]]) == 1
    assert len(by_tick[ticks[2]]) == 2
    assert len(by_tick[ticks[3]]) == 1
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred_id) is not None


def test_interpolate_cuboids__follows_a_moving_frame(db_session: Session) -> None:
    """An object stands still in `odom` while the frame of its cuboids rotates."""
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=_SECONDS)
    _add_rotating_frame(session=db_session, scene=scene)
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(
        session=db_session,
        scene=scene,
        tick_id=ticks[0],
        track=track,
        px=10.0,
        frame_id="base_link",
    )
    helpers.add_cuboid(
        session=db_session,
        scene=scene,
        tick_id=ticks[3],
        track=track,
        px=0.0,
        py=-10.0,
        yaw_deg=-90.0,
        frame_id="base_link",
    )

    _interpolate(session=db_session, ticks=ticks, track=track)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    for seq_number, position, yaw in ((1, (10.0, 0.0), 0.0), (2, (0.0, -10.0), -90.0)):
        details = by_tick[ticks[seq_number]][0].cuboid_3d_details
        assert details is not None
        assert details.frame_id == "base_link"
        assert (details.px, details.py) == pytest.approx(position, abs=1e-6)
        assert _yaw_deg(qz=details.qz, qw=details.qw) == pytest.approx(yaw, abs=1e-6)


def test_interpolate_cuboids__anchors_in_different_frames(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=_SECONDS)
    _add_rotating_frame(session=db_session, scene=scene)
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[0], track=track, px=10.0, frame_id="odom"
    )
    helpers.add_cuboid(
        session=db_session,
        scene=scene,
        tick_id=ticks[3],
        track=track,
        py=-10.0,
        yaw_deg=-90.0,
        frame_id="base_link",
    )

    _interpolate(session=db_session, ticks=ticks, track=track)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    for seq_number in (1, 2):
        details = by_tick[ticks[seq_number]][0].cuboid_3d_details
        assert details is not None
        assert details.frame_id == "odom"
        assert (details.px, details.py) == pytest.approx((10.0, 0.0), abs=1e-6)


def test_interpolate_cuboids__loads_transforms_of_the_affected_pair(
    db_session: Session, mocker: MockerFixture
) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(
        session=db_session,
        scene=scene,
        timestamps=[second * 1_000_000_000 for second in range(6)],
    )
    _add_rotating_frame(session=db_session, scene=scene)
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    for seq_number in (0, 2, 5):
        helpers.add_cuboid(
            session=db_session, scene=scene, tick_id=ticks[seq_number], track=track, px=10.0
        )
    load_world_poses = mocker.spy(world_poses, "load_world_poses")

    _interpolate(session=db_session, ticks=ticks, track=track, start=1, end=1)

    load_world_poses.assert_called_once()
    assert load_world_poses.call_args.kwargs["start_ns"] == 0
    assert load_world_poses.call_args.kwargs["end_ns"] == 2_000_000_000


_SECONDS: list[int | None] = [0, 1_000_000_000, 2_000_000_000, 3_000_000_000]


def _add_rotating_frame(session: Session, scene: helpers.Scene) -> None:
    """`base_link` is aligned with `odom` until 1 s and rotated by 90 degrees from 2 s."""
    dynamic_transform_resolver.create_many(
        session=session,
        rows=[
            DynamicTransformCreate(
                recording_id=scene.recording_id,
                parent="odom",
                child="base_link",
                timestamp_ns=timestamp_ns,
                qx=0.0,
                qy=0.0,
                qz=math.sin(math.radians(yaw) / 2),
                qw=math.cos(math.radians(yaw) / 2),
                tx=0.0,
                ty=0.0,
                tz=0.0,
            )
            for timestamp_ns, yaw in zip(_SECONDS, (0.0, 0.0, 90.0, 90.0))
            if timestamp_ns is not None
        ],
    )


def _yaw_deg(qz: float, qw: float) -> float:
    return math.degrees(2 * math.atan2(qz, qw))


def _interpolate(
    session: Session,
    ticks: list[UUID],
    track: ObjectTrackTable,
    start: int = 0,
    end: int | None = None,
) -> None:
    """Interpolate `ticks[start..end]` with the source of the track's first cuboid."""
    links = sequence_resolver.get_links_by_sample_ids(session=session, sample_ids={ticks[0]})
    by_tick = helpers.cuboids_by_tick(session=session, track=track)
    first_cuboid = next(by_tick[tick][0] for tick in ticks if tick in by_tick)
    object_track_service.interpolate_cuboids(
        session=session,
        object_track=track,
        interpolation_range=CuboidInterpolationRange(
            sequence_id=links[ticks[0]].sequence_sample_id,
            annotation_source_id=first_cuboid.annotation_collection_id,
            start_seq_number=start,
            end_seq_number=len(ticks) - 1 if end is None else end,
        ),
    )
