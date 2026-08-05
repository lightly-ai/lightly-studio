"""Tests for batch annotation label creation."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection


def test_create_batch__normalizes_and_deduplicates(db_session: Session) -> None:
    """Create normalized unique names and skip blank values."""
    collection = create_collection(session=db_session)

    result = annotation_label_resolver.create_batch(
        session=db_session,
        dataset_id=collection.dataset_id,
        label_names=[" cat ", "", "dog", "cat", "  "],
    )

    assert [label.annotation_label_name for label in result] == ["cat", "dog"]


def test_create_batch__skips_existing_labels(db_session: Session) -> None:
    """Return only newly created labels when a requested name already exists."""
    collection = create_collection(session=db_session)
    create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )

    result = annotation_label_resolver.create_batch(
        session=db_session,
        dataset_id=collection.dataset_id,
        label_names=["cat", "dog"],
    )

    assert [label.annotation_label_name for label in result] == ["dog"]
