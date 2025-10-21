"""Tests for annotation_label_resolver.get_by_label_name resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.conftest import AnnotationsTestData


def test_get_by_label_name__returns_label(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test getting annotations by label name."""
    annotation_label = annotation_label_resolver.get_by_label_name(
        session=db_session,
        label_name=annotations_test_data.annotation_labels[0].annotation_label_name,
    )

    assert annotation_label == annotations_test_data.annotation_labels[0]


def test_get_by_label_name__returns_none(
    db_session: Session,
) -> None:
    """Test returning None for a nonexistent label."""
    annotation_label = annotation_label_resolver.get_by_label_name(
        session=db_session,
        label_name="nonexistent_label_name",
    )

    assert annotation_label is None
