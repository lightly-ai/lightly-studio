from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.mcap_sequence_tracks import TrackAnnotationView
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import annotation_resolver, group_resolver, object_track_resolver
from lightly_studio.services import recording_service
from lightly_studio.services.recording_service import world_poses
from tests.helpers_resolvers import create_annotation_label, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers
from tests.resolvers.mcap_group_sequence_resolver.helpers import McapSequenceFixture


@dataclass
class _Setup:
    fixture: McapSequenceFixture
    track_id: UUID
    source_id: UUID


def test_extend_sequence_track__both_directions(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=8, covered=[3, 4])

    created = _extend(session=db_session, setup=setup, start=1, end=6)

    assert created == [1, 2, 5, 6]
    annotations = _track_annotations(session=db_session, setup=setup)
    assert [(a.seq_number, a.interpolated) for a in annotations] == [
        (1, False),
        (2, True),
        (3, False),
        (4, False),
        (5, True),
        (6, False),
    ]


def test_extend_sequence_track__copies_boundary_cuboid(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=4, covered=[1])

    _extend(session=db_session, setup=setup, start=0, end=3)

    cuboids = _cuboids_by_seq_number(session=db_session, setup=setup)
    assert set(cuboids) == {0, 1, 2, 3}
    assert len({cuboids[seq_number] for seq_number in cuboids}) == 1


def test_extend_sequence_track__interpolates_up_to_the_new_edge(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=4, covered=[0, 1])
    (boundary,) = [
        a for a in _track_annotations(session=db_session, setup=setup) if a.seq_number == 1
    ]
    annotation = annotation_resolver.get_by_id(
        session=db_session, annotation_id=boundary.annotation_id
    )
    assert annotation is not None
    assert annotation.cuboid_3d_details is not None
    annotation_resolver.update_cuboid_3d(
        session=db_session,
        annotation_id=boundary.annotation_id,
        cuboid_3d=Cuboid3DCreate.model_validate(
            annotation.cuboid_3d_details.model_dump() | {"px": 4.0, "interpolated": True}
        ),
    )

    _extend(session=db_session, setup=setup, start=0, end=3)

    cuboids = _cuboids_by_seq_number(session=db_session, setup=setup)
    assert [cuboids[seq_number][0] for seq_number in range(4)] == pytest.approx(
        [1.0, 2.0, 3.0, 4.0]
    )


def test_extend_sequence_track__loads_transforms_of_the_new_ticks(
    db_session: Session, mocker: MockerFixture
) -> None:
    # Tick `n` has the timestamp 1_000 + n.
    setup = _create_track(session=db_session, tick_count=8, covered=[3, 4])
    load_world_poses = mocker.spy(world_poses, "load_world_poses")

    _extend(session=db_session, setup=setup, start=1, end=4)

    boundary_copy_call = load_world_poses.call_args_list[0]
    assert boundary_copy_call.kwargs["start_ns"] == 1_001
    assert boundary_copy_call.kwargs["end_ns"] == 1_003


def test_extend_sequence_track__shrink_makes_new_edge_manual(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=7, covered=[3])
    _extend(session=db_session, setup=setup, start=0, end=6)

    assert _extend(session=db_session, setup=setup, start=1, end=4) == []

    annotations = _track_annotations(session=db_session, setup=setup)
    assert [(a.seq_number, a.interpolated) for a in annotations] == [
        (1, False),
        (2, True),
        (3, False),
        (4, False),
    ]


def test_extend_sequence_track__shrink_keeps_untouched_edge(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=5, covered=[0])
    _extend(session=db_session, setup=setup, start=0, end=4)
    _set_interpolated(session=db_session, setup=setup, seq_number=0)

    _extend(session=db_session, setup=setup, start=0, end=2)

    annotations = _track_annotations(session=db_session, setup=setup)
    assert [(a.seq_number, a.interpolated) for a in annotations] == [
        (0, True),
        (1, True),
        (2, False),
    ]


def test_extend_sequence_track__shrink_into_gap_adds_manual_edge(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=5, covered=[0, 4])

    assert _extend(session=db_session, setup=setup, start=2, end=4) == [2, 3]

    annotations = _track_annotations(session=db_session, setup=setup)
    assert [(a.seq_number, a.interpolated) for a in annotations] == [
        (2, False),
        (3, True),
        (4, False),
    ]


def test_extend_sequence_track__retry_creates_nothing(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=6, covered=[2])

    assert _extend(session=db_session, setup=setup, start=2, end=5) == [3, 4, 5]
    assert _extend(session=db_session, setup=setup, start=2, end=5) == []

    annotations = _track_annotations(session=db_session, setup=setup)
    assert [a.seq_number for a in annotations] == [2, 3, 4, 5]


def test_extend_sequence_track__inside_range_is_a_no_op(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=6, covered=[1, 4])

    # Tick 2 and 3 are a gap inside the track: only outward extension is supported.
    assert _extend(session=db_session, setup=setup, start=1, end=4) == []
    assert [a.seq_number for a in _track_annotations(session=db_session, setup=setup)] == [1, 4]


def test_extend_sequence_track__rejects_unknown_ticks(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[1])

    with pytest.raises(ValueError, match="do not exist"):
        _extend(session=db_session, setup=setup, start=0, end=9)
    with pytest.raises(ValueError, match="must not be greater"):
        _extend(session=db_session, setup=setup, start=2, end=1)
    assert [a.seq_number for a in _track_annotations(session=db_session, setup=setup)] == [1]


def test_extend_sequence_track__rejects_unknown_track(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[1])
    other = _create_track(session=db_session, tick_count=3, covered=[1])

    with pytest.raises(ValueError, match="no annotations from this source"):
        recording_service.extend_sequence_track(
            session=db_session,
            dataset_id=setup.fixture.sequence_collection.dataset_id,
            sequence_id=setup.fixture.sample_id,
            track_id=other.track_id,
            annotation_source_id=setup.source_id,
            start_seq_number=0,
            end_seq_number=2,
        )


def test_extend_sequence_track__unknown_sequence(db_session: Session) -> None:
    setup = _create_track(session=db_session, tick_count=3, covered=[1])

    result = recording_service.extend_sequence_track(
        session=db_session,
        dataset_id=setup.fixture.sequence_collection.dataset_id,
        sequence_id=setup.fixture.group_collection.collection_id,
        track_id=setup.track_id,
        annotation_source_id=setup.source_id,
        start_seq_number=0,
        end_seq_number=2,
    )

    assert result is None


def _extend(session: Session, setup: _Setup, start: int, end: int) -> list[int] | None:
    return recording_service.extend_sequence_track(
        session=session,
        dataset_id=setup.fixture.sequence_collection.dataset_id,
        sequence_id=setup.fixture.sample_id,
        track_id=setup.track_id,
        annotation_source_id=setup.source_id,
        start_seq_number=start,
        end_seq_number=end,
    )


def _set_interpolated(session: Session, setup: _Setup, seq_number: int) -> None:
    (item,) = [
        a for a in _track_annotations(session=session, setup=setup) if a.seq_number == seq_number
    ]
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=item.annotation_id)
    assert annotation is not None
    assert annotation.cuboid_3d_details is not None
    annotation_resolver.update_cuboid_3d(
        session=session,
        annotation_id=item.annotation_id,
        cuboid_3d=Cuboid3DCreate.model_validate(
            annotation.cuboid_3d_details.model_dump() | {"interpolated": True}
        ),
    )


def _track_annotations(session: Session, setup: _Setup) -> list[TrackAnnotationView]:
    result = recording_service.get_sequence_tracks(
        session=session,
        dataset_id=setup.fixture.sequence_collection.dataset_id,
        sequence_id=setup.fixture.sample_id,
    )
    assert result is not None
    (track,) = [t for t in result.tracks if t.object_track_id == setup.track_id]
    return track.annotations


def _cuboids_by_seq_number(session: Session, setup: _Setup) -> dict[int, tuple[float, ...]]:
    cuboids: dict[int, tuple[float, ...]] = {}
    for item in _track_annotations(session=session, setup=setup):
        annotation = annotation_resolver.get_by_id(
            session=session, annotation_id=item.annotation_id
        )
        assert annotation is not None
        assert annotation.cuboid_3d_details is not None
        details = annotation.cuboid_3d_details
        cuboids[item.seq_number] = (
            details.px,
            details.py,
            details.pz,
            details.qw,
            details.sx,
            details.sy,
            details.sz,
        )
    return cuboids


def _create_track(session: Session, tick_count: int, covered: list[int]) -> _Setup:
    """Creates a sequence whose track holds a drawn cuboid on each `covered` tick."""
    fixture = helpers.create_mcap_sequence(session=session)
    group_ids = group_resolver.create_many(
        session=session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set() for _ in range(tick_count)],
    )
    for seq_number, group_id in enumerate(group_ids):
        session.add(
            SampleSequenceLinkTable(
                sample_id=group_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
                timestamp_ns=1_000 + seq_number,
            )
        )
    label = create_annotation_label(
        session=session,
        root_collection_id=fixture.group_collection.collection_id,
        label_name="truck",
    )
    track_id = object_track_resolver.create_many(
        session=session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=1, dataset_id=fixture.sequence_collection.dataset_id
            )
        ],
    )[0]
    annotation_resolver.create_many(
        session=session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[seq_number],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            )
            for seq_number in covered
        ],
        collection_name="ground_truth",
    )
    session.commit()
    tracks = recording_service.get_sequence_tracks(
        session=session,
        dataset_id=fixture.sequence_collection.dataset_id,
        sequence_id=fixture.sample_id,
    )
    assert tracks is not None
    return _Setup(
        fixture=fixture,
        track_id=track_id,
        source_id=tracks.tracks[-1].annotation_source_id,
    )
