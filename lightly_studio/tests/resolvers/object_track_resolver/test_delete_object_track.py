"""Tests for delete_track resolver."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_delete_object_track__unlinks_annotations(test_db: Session) -> None:
    """Test that deleting a track unlinks all its annotations."""
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

    track = object_track_resolver.create_object_track(
        session=test_db,
        object_track_number=1,
        dataset_id=collection.collection_id,
    )

    object_track_resolver.add_annotation_to_object_track(
        session=test_db,
        annotation_id=annotation.sample_id,
        object_track=track,
    )

    object_track_resolver.delete_object_track(
        session=test_db,
        object_track_id=track.object_track_id,
    )

    # Track should be gone.
    assert (
        object_track_resolver.get_by_id(session=test_db, object_track_id=track.object_track_id)
        is None
    )

    # Annotation should still exist but be unlinked.
    fetched = annotation_resolver.get_by_id(session=test_db, annotation_id=annotation.sample_id)
    assert fetched is not None
    assert fetched.object_track_id is None


def test_delete_object_track__not_found(test_db: Session) -> None:
    """Test that ValueError is raised for a non-existent track ID."""
    with pytest.raises(ValueError, match="not found"):
        object_track_resolver.delete_object_track(
            session=test_db,
            object_track_id=uuid4(),
        )
