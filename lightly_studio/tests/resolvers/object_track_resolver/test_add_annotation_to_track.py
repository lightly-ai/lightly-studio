"""Tests for add_annotation_to_track resolver."""

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


def test_add_annotation_to_track(test_db: Session) -> None:
    """Test linking an object detection annotation to a track."""
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

    # Refresh annotation after track creation commit expired it.
    test_db.refresh(annotation)

    result = object_track_resolver.add_annotation_to_track(
        session=test_db,
        annotation=annotation,
        track=track,
    )

    assert result.object_track_id == track.object_track_id

    # Verify persisted in database.
    fetched = annotation_resolver.get_by_id(
        session=test_db, annotation_id=annotation.sample_id
    )
    assert fetched is not None
    assert fetched.object_track_id == track.object_track_id
