"""Tests for annotation labels with annotation counts."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_all_with_counts(db_session: Session) -> None:
    """Return zero-count and used annotation labels in creation order."""
    collection = create_collection(session=db_session)
    cat = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )
    create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/tmp/counts.png",
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=cat.annotation_label_id,
    )

    result = annotation_label_resolver.get_all_with_counts(
        session=db_session,
        dataset_id=collection.dataset_id,
    )

    assert [(label.annotation_label_name, label.annotation_count) for label in result] == [
        ("cat", 1),
        ("dog", 0),
    ]


def test_get_all_with_counts__no_labels(db_session: Session) -> None:
    """Return an empty list when the dataset has no annotation labels."""
    collection = create_collection(session=db_session)

    result = annotation_label_resolver.get_all_with_counts(
        session=db_session,
        dataset_id=collection.dataset_id,
    )

    assert result == []
