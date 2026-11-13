"""Tests for update_parent_track resolver."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update_parent_track__set_parent(db_session: Session) -> None:
    """Setting a parent creates a replacement track with the parent link."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    parent_id, child_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id
    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation_id,
        object_track_id=child_id,
    )

    result = object_track_resolver.update_parent_track(
        session=db_session,
        dataset_id=collection.dataset_id,
        object_track_id=child_id,
        parent_object_track_id=parent_id,
    )

    assert result is not None
    assert result.parent_object_track_id == parent_id
    assert result.object_track_number == 2
    # Old track is deleted, annotation moved to replacement.
    assert object_track_resolver.get_by_id(session=db_session, object_track_id=child_id) is None
    fetched = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id)
    assert fetched is not None
    assert fetched.object_track_id == result.object_track_id


def test_update_parent_track__remove_parent(db_session: Session) -> None:
    """Setting parent to None removes the parent link."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

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

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    object_track_resolver.add_annotation_to_object_track(
        session=db_session,
        annotation_id=annotation.sample_id,
        object_track_id=child_id,
    )

    result = object_track_resolver.update_parent_track(
        session=db_session,
        dataset_id=collection.dataset_id,
        object_track_id=child_id,
        parent_object_track_id=None,
    )

    assert result is not None
    assert result.parent_object_track_id is None
    assert result.object_track_number == 2


def test_update_parent_track__not_found(db_session: Session) -> None:
    """Returns None when the track does not belong to the dataset."""
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)

    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id)],
    )[0]

    result = object_track_resolver.update_parent_track(
        session=db_session,
        dataset_id=other_collection.dataset_id,
        object_track_id=track_id,
        parent_object_track_id=None,
    )

    assert result is None


def test_update_parent_track__same_parent_is_noop(db_session: Session) -> None:
    """Returns the existing track unchanged when the parent is already set."""
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

    result = object_track_resolver.update_parent_track(
        session=db_session,
        dataset_id=collection.dataset_id,
        object_track_id=child_id,
        parent_object_track_id=parent_id,
    )

    assert result is not None
    assert result.object_track_id == child_id


def test_update_parent_track__migrates_descendants(db_session: Session) -> None:
    """Child tracks are re-parented to the replacement track."""
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    grandparent_id, parent_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )
    child_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=3,
                dataset_id=collection.dataset_id,
                parent_object_track_id=parent_id,
            )
        ],
    )[0]

    # Each track needs an annotation so it can be fully replaced.
    for track_id in [parent_id, child_id]:
        img = create_image(session=db_session, collection_id=collection.collection_id)
        ann = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=img.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        object_track_resolver.add_annotation_to_object_track(
            session=db_session, annotation_id=ann.sample_id, object_track_id=track_id
        )

    result = object_track_resolver.update_parent_track(
        session=db_session,
        dataset_id=collection.dataset_id,
        object_track_id=parent_id,
        parent_object_track_id=grandparent_id,
    )

    assert result is not None
    assert result.parent_object_track_id == grandparent_id
    # Old parent and child tracks are replaced.
    assert object_track_resolver.get_by_id(session=db_session, object_track_id=parent_id) is None
    assert object_track_resolver.get_by_id(session=db_session, object_track_id=child_id) is None
    # The descendant's replacement points to the new parent.
    all_tracks = object_track_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )
    descendant = [t for t in all_tracks if t.object_track_number == 3]
    assert len(descendant) == 1
    assert descendant[0].parent_object_track_id == result.object_track_id


def test_update_parent_track__no_orphan_track_on_early_failure(
    db_session: Session, mocker: MockerFixture
) -> None:
    """No replacement track is persisted when migration fails before any annotation commits.

    The replacement track is only flushed (not committed) until the first
    annotation migration commits. If the migration raises before that point,
    a session rollback removes the flushed track cleanly.
    """
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)

    parent_id, track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(object_track_number=1, dataset_id=collection.dataset_id),
            ObjectTrackCreate(object_track_number=2, dataset_id=collection.dataset_id),
        ],
    )

    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    annotation_id = annotation.sample_id
    object_track_resolver.add_annotation_to_object_track(
        session=db_session, annotation_id=annotation_id, object_track_id=track_id
    )

    tracks_before = object_track_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )
    track_ids_before = {t.object_track_id for t in tracks_before}

    # Fail on the first annotation migration — before delete_annotation commits.
    mocker.patch.object(
        annotation_helper,
        "update_annotation_object",
        side_effect=RuntimeError("simulated migration failure"),
    )

    with pytest.raises(RuntimeError, match="simulated migration failure"):
        object_track_resolver.update_parent_track(
            session=db_session,
            dataset_id=collection.dataset_id,
            object_track_id=track_id,
            parent_object_track_id=parent_id,
        )

    # Roll back the dirty session, mirroring what the production session
    # manager does when an exception propagates out of a route handler.
    db_session.rollback()

    # Original track and annotation are unchanged.
    track = object_track_resolver.get_by_id(session=db_session, object_track_id=track_id)
    assert track is not None
    assert track.parent_object_track_id is None

    fetched = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation_id)
    assert fetched is not None
    assert fetched.object_track_id == track_id

    # No orphan replacement track was left behind.
    tracks_after = object_track_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )
    assert {t.object_track_id for t in tracks_after} == track_ids_before
