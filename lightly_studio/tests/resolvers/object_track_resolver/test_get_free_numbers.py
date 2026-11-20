from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_collection


def test_get_free_numbers(db_session: Session) -> None:
    dataset_id = create_collection(session=db_session).dataset_id
    other_dataset_id = create_collection(session=db_session).dataset_id
    object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=dataset_id),
            ObjectTrackCreate(object_track_number=3, dataset_id=dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=other_dataset_id),
        ],
    )

    numbers = object_track_resolver.get_free_numbers(
        session=db_session, dataset_id=dataset_id, count=3
    )

    assert numbers == [2, 4, 5]
