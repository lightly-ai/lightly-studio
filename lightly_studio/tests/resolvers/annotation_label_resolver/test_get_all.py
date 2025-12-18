"""Tests for annotation_label_resolver - get_all functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_dataset,
)


def test_get_all(
    db_session: Session,
) -> None:
    dataset_id_1 = create_dataset(session=db_session).dataset_id
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_1, label_name="dog")
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_1, label_name="zebra")
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_1, label_name="cat")
    dataset_id_2 = create_dataset(session=db_session).dataset_id
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_2, label_name="bird")
    labels = annotation_label_resolver.get_all(
        session=db_session,
        root_dataset_id=dataset_id_1,
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
    dataset_id_1 = create_dataset(session=db_session).dataset_id
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_1, label_name="dog")
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_1, label_name="zebra")
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_1, label_name="cat")
    dataset_id_2 = create_dataset(session=db_session).dataset_id
    create_annotation_label(session=db_session, root_dataset_id=dataset_id_2, label_name="bird")
    labels = annotation_label_resolver.get_all_sorted_alphabetically(
        session=db_session,
        root_dataset_id=dataset_id_1,
    )
    # Annotation Labels should be sorted alphabetically
    assert [label.annotation_label_name for label in labels] == [
        "cat",
        "dog",
        "zebra",
    ]
