from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_create_with_next_number__numbers_per_dataset(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other")

    first = object_track_resolver.create_with_next_number(
        session=db_session, dataset_id=collection.dataset_id
    )
    object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=10, dataset_id=collection.dataset_id)],
    )
    after_ten = object_track_resolver.create_with_next_number(
        session=db_session, dataset_id=collection.dataset_id
    )
    other = object_track_resolver.create_with_next_number(
        session=db_session, dataset_id=other_collection.dataset_id
    )

    assert first.object_track_number == 1
    assert after_ten.object_track_number == 11
    assert other.object_track_number == 1
    assert first.dataset_id == collection.dataset_id


def test_delete_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    track = object_track_resolver.create_with_next_number(
        session=db_session, dataset_id=collection.dataset_id
    )

    object_track_resolver.delete_by_id(session=db_session, object_track_id=track.object_track_id)
    object_track_resolver.delete_by_id(session=db_session, object_track_id=track.object_track_id)

    assert (
        object_track_resolver.get_by_id(session=db_session, object_track_id=track.object_track_id)
        is None
    )
