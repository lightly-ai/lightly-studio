"""Tests for get_all_by_dataset resolver."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_get_all_by_dataset(test_db: Session) -> None:
    """Test retrieving all tracks for a dataset, ordered by track number."""
    collection = create_collection(session=test_db)

    # Create tracks in reverse order to verify ordering.
    for num in [3, 1, 2]:
        object_track_resolver.create_track(
            session=test_db,
            object_track_number=num,
            dataset_id=collection.collection_id,
        )

    tracks = object_track_resolver.get_all_by_dataset(
        session=test_db,
        dataset_id=collection.collection_id,
    )

    assert len(tracks) == 3
    assert [t.object_track_number for t in tracks] == [1, 2, 3]


def test_get_all_by_dataset__empty(test_db: Session) -> None:
    """Test empty result when no tracks exist for a dataset."""
    tracks = object_track_resolver.get_all_by_dataset(
        session=test_db,
        dataset_id=uuid4(),
    )
    assert len(tracks) == 0


def test_get_all_by_dataset__different_datasets(test_db: Session) -> None:
    """Test that tracks are scoped to their dataset."""
    collection_a = create_collection(session=test_db, collection_name="dataset_a")
    collection_b = create_collection(session=test_db, collection_name="dataset_b")

    object_track_resolver.create_track(
        session=test_db, object_track_number=1, dataset_id=collection_a.collection_id
    )
    object_track_resolver.create_track(
        session=test_db, object_track_number=2, dataset_id=collection_b.collection_id
    )

    tracks_a = object_track_resolver.get_all_by_dataset(
        session=test_db, dataset_id=collection_a.collection_id
    )
    tracks_b = object_track_resolver.get_all_by_dataset(
        session=test_db, dataset_id=collection_b.collection_id
    )

    assert len(tracks_a) == 1
    assert tracks_a[0].object_track_number == 1
    assert len(tracks_b) == 1
    assert tracks_b[0].object_track_number == 2
