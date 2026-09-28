"""Tests for create_many resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_create_many(db_session: Session) -> None:
    """Test creating tracks and verifying returned fields."""
    collection = create_collection(session=db_session)

    track_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=10, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=20, dataset_id=collection.dataset_id),
        ],
    )

    assert len(track_ids) == 2

    track1 = object_track_resolver.get_by_id(
        session=db_session,
        object_track_id=track_ids[0],
    )
    assert track1 is not None
    assert track1.object_track_number == 10
    assert track1.dataset_id == collection.dataset_id

    track2 = object_track_resolver.get_by_id(
        session=db_session,
        object_track_id=track_ids[1],
    )
    assert track2 is not None
    assert track2.object_track_number == 20
    assert track2.dataset_id == collection.dataset_id


def test_create_many__source_and_parent_track(db_session: Session) -> None:
    """Test persisting source_track_id and parent_object_track_id."""
    collection = create_collection(session=db_session)

    parent_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=1,
                dataset_id=collection.dataset_id,
                source_track_id=42,
            )
        ],
    )
    child_ids = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=2,
                dataset_id=collection.dataset_id,
                source_track_id=43,
                parent_object_track_id=parent_ids[0],
            )
        ],
    )

    parent = object_track_resolver.get_by_id(session=db_session, object_track_id=parent_ids[0])
    child = object_track_resolver.get_by_id(session=db_session, object_track_id=child_ids[0])
    assert parent is not None
    assert parent.source_track_id == 42
    assert parent.parent_object_track_id is None
    assert child is not None
    assert child.source_track_id == 43
    assert child.parent_object_track_id == parent_ids[0]
