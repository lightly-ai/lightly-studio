"""Tests for annotation_label_resolver - get_all functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
)


def test_get_all(
    db_session: Session,
) -> None:
    create_annotation_label(session=db_session, annotation_label_name="dog")
    create_annotation_label(session=db_session, annotation_label_name="zebra")
    create_annotation_label(session=db_session, annotation_label_name="cat")
    labels = annotation_label_resolver.get_all(
        session=db_session,
    )
    # Annotation Labels should be sorted by creation time
    assert [label.annotation_label_name for label in labels] == [
        "dog",
        "zebra",
        "cat",
    ]


def test_get_all_sorted_alphabetically(
    db_session: Session,
) -> None:
    create_annotation_label(session=db_session, annotation_label_name="dog")
    create_annotation_label(session=db_session, annotation_label_name="zebra")
    create_annotation_label(session=db_session, annotation_label_name="cat")
    labels = annotation_label_resolver.get_all_sorted_alphabetically(
        session=db_session,
    )
    # Annotation Labels should be sorted alphabetically
    assert [label.annotation_label_name for label in labels] == [
        "cat",
        "dog",
        "zebra",
    ]
