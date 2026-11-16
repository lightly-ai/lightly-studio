"""Tests for annotation_label_resolver.set_color resolver."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection


def test_set_color(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )

    updated = annotation_label_resolver.set_color(
        session=db_session, label_id=label.annotation_label_id, color="#ff0000", alpha=0.5
    )

    assert updated is not None
    assert updated.color == "#ff0000"
    assert updated.alpha == 0.5
    reread = annotation_label_resolver.get_by_id(
        session=db_session, label_id=label.annotation_label_id
    )
    assert reread is not None
    assert reread.color == "#ff0000"
    assert reread.alpha == 0.5


def test_set_color__clear(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )
    annotation_label_resolver.set_color(
        session=db_session, label_id=label.annotation_label_id, color="#ff0000", alpha=0.5
    )

    updated = annotation_label_resolver.set_color(
        session=db_session, label_id=label.annotation_label_id, color=None, alpha=None
    )

    assert updated is not None
    assert updated.color is None
    assert updated.alpha is None


def test_set_color__unknown_label(db_session: Session) -> None:
    updated = annotation_label_resolver.set_color(
        session=db_session, label_id=uuid4(), color="#ff0000", alpha=0.5
    )

    assert updated is None
