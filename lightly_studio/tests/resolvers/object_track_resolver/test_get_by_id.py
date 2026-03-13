"""Tests for get_by_id resolver."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_get_by_id(db_session: Session) -> None:
    """Test retrieving a track by its ID."""
    collection = create_collection(session=db_session)
    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=99, dataset_id=collection.collection_id)],
    )[0]
    assert track_id is not None
    result = object_track_resolver.get_by_id(
        session=db_session,
        object_track_id=track_id,
    )

    assert result is not None
    assert result.object_track_id == track_id
    assert result.object_track_number == 99
    assert result.dataset_id == collection.collection_id


def test_get_by_id__not_found(db_session: Session) -> None:
    """Test that None is returned for a non-existent ID."""
    result = object_track_resolver.get_by_id(
        session=db_session,
        object_track_id=uuid4(),
    )
    assert result is None
