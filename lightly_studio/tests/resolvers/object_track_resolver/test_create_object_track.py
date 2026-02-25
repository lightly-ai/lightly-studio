"""Tests for create_object_track resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_create_object_track(test_db: Session) -> None:
    """Test creating a track and verifying returned fields."""
    collection = create_collection(session=test_db)

    track = object_track_resolver.create_object_track(
        session=test_db,
        object_track_number=1,
        dataset_id=collection.collection_id,
    )

    assert track.object_track_id is not None
    assert track.object_track_number == 1
    assert track.dataset_id == collection.collection_id


def test_create_object_track__multiple_tracks(test_db: Session) -> None:
    """Test creating multiple tracks with different numbers."""
    collection = create_collection(session=test_db)

    tracks = [
        object_track_resolver.create_object_track(
            session=test_db,
            object_track_number=i,
            dataset_id=collection.collection_id,
        )
        for i in range(3)
    ]

    assert len(tracks) == 3
    for i, track in enumerate(tracks):
        assert track.object_track_number == i
        assert track.dataset_id == collection.collection_id
    # All IDs should be unique.
    ids = {t.object_track_id for t in tracks}
    assert len(ids) == 3
