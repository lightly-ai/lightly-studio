"""Tests for get_by_id resolver."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_get_all_by_dataset_id(test_db: Session) -> None:
    """Test retrieving all tracks for a dataset."""
    collection = create_collection(session=test_db)
    collection_2 = create_collection(session=test_db)
    track_ids = object_track_resolver.create_many(
        session=test_db,
        tracks=[ObjectTrackCreate(object_track_number=99, dataset_id=collection.collection_id),
                ObjectTrackCreate(object_track_number=100, dataset_id=collection.collection_id),
                ObjectTrackCreate(object_track_number=101, dataset_id=collection_2.collection_id)],
    )
    assert len(track_ids) == 3

    result = object_track_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=collection.collection_id,
    )

    assert len(result) == 2
    assert result[0].object_track_id == track_ids[0]
    assert result[1].object_track_id == track_ids[1]


def test_get_all_by_dataset_id__dataset_id_not_found(test_db: Session) -> None:
    """Test that an empty list is returned for a non-existent dataset ID."""
    result = object_track_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=uuid4(),
    )
    assert len(result) == 0
