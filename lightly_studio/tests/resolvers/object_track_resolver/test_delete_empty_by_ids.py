"""Tests for delete_empty_by_ids resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_delete_empty_by_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    empty_id, kept_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )

    deleted_count = object_track_resolver.delete_empty_by_ids(
        session=db_session, object_track_ids=[empty_id]
    )

    assert deleted_count == 1
    assert _track_ids(session=db_session, dataset_id=collection.dataset_id) == [kept_id]


def test_delete_empty_by_ids__keeps_track_with_annotation(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]
    object_track_resolver.add_annotation_to_object_track(
        session=db_session, annotation_id=annotation.sample_id, object_track_id=track_id
    )

    deleted_count = object_track_resolver.delete_empty_by_ids(
        session=db_session, object_track_ids=[track_id]
    )

    assert deleted_count == 0
    assert _track_ids(session=db_session, dataset_id=collection.dataset_id) == [track_id]


def test_delete_empty_by_ids__deletes_empty_parent_track(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    parent_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]
    child_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=2,
                dataset_id=collection.dataset_id,
                parent_object_track_id=parent_id,
            )
        ],
    )[0]

    deleted_count = object_track_resolver.delete_empty_by_ids(
        session=db_session, object_track_ids=[child_id]
    )

    assert deleted_count == 2
    assert _track_ids(session=db_session, dataset_id=collection.dataset_id) == []


def _track_ids(session: Session, dataset_id: UUID) -> list[UUID]:
    return [
        track.object_track_id
        for track in object_track_resolver.get_all_by_dataset_id(
            session=session, dataset_id=dataset_id
        )
    ]
