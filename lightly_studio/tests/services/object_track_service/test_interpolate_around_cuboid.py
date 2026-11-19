from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.services import object_track_service
from tests.services.object_track_service import helpers


def test_interpolate_around_cuboid__interpolates_both_sides(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=list(range(0, 50, 10)))
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    for seq_number in (0, 4):
        helpers.add_cuboid(
            session=db_session, scene=scene, tick_id=ticks[seq_number], track=track, px=0.0
        )
    for seq_number in (1, 3):
        helpers.add_cuboid(
            session=db_session,
            scene=scene,
            tick_id=ticks[seq_number],
            track=track,
            px=0.0,
            interpolated=True,
        )
    middle_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[2], track=track, px=8.0
    )

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=middle_id)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    assert helpers.px_of(by_tick[ticks[1]][0]) == pytest.approx(4.0)
    assert helpers.px_of(by_tick[ticks[3]][0]) == pytest.approx(4.0)


def test_interpolate_around_cuboid__keeps_other_pairs(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=list(range(0, 50, 10)))
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    first_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[0], track=track, px=4.0
    )
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[1], track=track, px=9.0, interpolated=True
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[2], track=track, px=0.0)
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[3], track=track, px=7.0, interpolated=True
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[4], track=track, px=0.0)

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=first_id)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    assert helpers.px_of(by_tick[ticks[1]][0]) == pytest.approx(2.0)
    assert helpers.px_of(by_tick[ticks[3]][0]) == pytest.approx(7.0)


def test_interpolate_around_cuboid__fills_empty_ticks(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=list(range(0, 50, 10)))
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, px=0.0)
    end_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[4], track=track, px=8.0
    )

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=end_id)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    assert [helpers.px_of(by_tick[ticks[n]][0]) for n in range(5)] == pytest.approx(
        [0.0, 2.0, 4.0, 6.0, 8.0]
    )


def test_interpolate_around_cuboid__ignores_other_sources(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    first_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[0], track=track, source="gt"
    )
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[2], track=track, source="predictions"
    )

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=first_id)

    assert ticks[1] not in helpers.cuboids_by_tick(session=db_session, track=track)


def test_interpolate_around_cuboid__interpolated_cuboid(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track, px=0.0)
    middle_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[1], track=track, px=9.0, interpolated=True
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[2], track=track, px=0.0)

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=middle_id)

    by_tick = helpers.cuboids_by_tick(session=db_session, track=track)
    assert helpers.px_of(by_tick[ticks[1]][0]) == pytest.approx(9.0)


def test_interpolate_around_cuboid__single_manual_cuboid(db_session: Session) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    only_id = helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[1], track=track)

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=only_id)

    assert list(helpers.cuboids_by_tick(session=db_session, track=track)) == [ticks[1]]


def test_interpolate_around_cuboid__replaces_interpolated_cuboid_on_its_tick(
    db_session: Session,
) -> None:
    scene = helpers.create_scene(session=db_session)
    ticks = helpers.add_sequence(session=db_session, scene=scene, timestamps=[0, 10, 20])
    track = helpers.create_track(session=db_session, scene=scene, number=1)
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[0], track=track)
    helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[1], track=track, interpolated=True
    )
    helpers.add_cuboid(session=db_session, scene=scene, tick_id=ticks[2], track=track)
    middle_id = helpers.add_cuboid(
        session=db_session, scene=scene, tick_id=ticks[1], track=track, px=5.0
    )

    object_track_service.interpolate_around_cuboid(session=db_session, annotation_id=middle_id)

    assert [
        c.sample_id for c in helpers.cuboids_by_tick(session=db_session, track=track)[ticks[1]]
    ] == [middle_id]
