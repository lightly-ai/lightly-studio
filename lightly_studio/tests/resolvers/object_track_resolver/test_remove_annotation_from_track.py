"""Tests for remove_annotation_from_track resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_remove_annotation_from_track(test_db: Session) -> None:
    """Test unlinking an annotation from its track."""
    collection = create_collection(session=test_db)
    image = create_image(session=test_db, collection_id=collection.collection_id)
    label = create_annotation_label(session=test_db, dataset_id=collection.collection_id)

    annotation = create_annotation(
        session=test_db,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    track = object_track_resolver.create_track(
        session=test_db,
        object_track_number=1,
        dataset_id=collection.collection_id,
    )

    # First link, then unlink.
    linked = object_track_resolver.add_annotation_to_track(
        session=test_db,
        annotation_id=annotation.sample_id,
        track=track,
    )

    # Re-fetch the annotation from DB to get a fresh instance.
    linked_fetched = annotation_resolver.get_by_id(session=test_db, annotation_id=linked.sample_id)
    assert linked_fetched is not None
    assert linked_fetched.object_track_id == track.object_track_id

    result = object_track_resolver.remove_annotation_from_track(
        session=test_db,
        annotation_id=linked_fetched.sample_id,
    )

    assert result.object_track_id is None

    # Verify persisted in database.
    fetched = annotation_resolver.get_by_id(session=test_db, annotation_id=annotation.sample_id)
    assert fetched is not None
    assert fetched.object_track_id is None
