"""Tests for annotation_label_resolver.get_by_ids."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection


def test_get_by_ids(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label_a = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="a",
    )
    label_b = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="b",
    )

    result = annotation_label_resolver.get_by_ids(
        session=db_session,
        ids=[label_b.annotation_label_id, uuid4(), label_a.annotation_label_id],
    )

    assert [label.annotation_label_id for label in result] == [
        label_b.annotation_label_id,
        label_a.annotation_label_id,
    ]


def test_get_by_ids__empty(db_session: Session) -> None:
    result = annotation_label_resolver.get_by_ids(session=db_session, ids=[])

    assert result == []
