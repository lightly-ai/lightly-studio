"""Tests for create_many resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_create_many(test_db: Session) -> None:
    """Test creating tracks and verifying returned fields."""
    collection = create_collection(session=test_db)

    track_ids = object_track_resolver.create_many(
        session=test_db,
        tracks=[
            ObjectTrackCreate(object_track_number=10, dataset_id=collection.collection_id),
            ObjectTrackCreate(object_track_number=20, dataset_id=collection.collection_id),
        ],
    )

    assert len(track_ids) == 2

    track1 = object_track_resolver.get_by_id(
        session=test_db,
        object_track_id=track_ids[0],
    )
    assert track1 is not None
    assert track1.object_track_number == 10
    assert track1.dataset_id == collection.collection_id

    track2 = object_track_resolver.get_by_id(
        session=test_db,
        object_track_id=track_ids[1],
    )
    assert track2 is not None
    assert track2.object_track_number == 20
    assert track2.dataset_id == collection.collection_id
