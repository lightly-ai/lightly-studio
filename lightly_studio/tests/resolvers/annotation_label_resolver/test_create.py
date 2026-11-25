"""Tests for annotation_label_resolver.create resolver."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import create_collection


def test_create(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    label = annotation_label_resolver.create(
        session=db_session,
        label=AnnotationLabelCreate(dataset_id=collection.dataset_id, annotation_label_name="boat"),
    )

    assert label.dataset_id == collection.dataset_id
    assert label.annotation_label_name == "boat"


def test_create__name_taken(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    annotation_label_resolver.create(
        session=db_session,
        label=AnnotationLabelCreate(dataset_id=collection.dataset_id, annotation_label_name="boat"),
    )

    with pytest.raises(IntegrityError, match="Annotation label already exists"):
        annotation_label_resolver.create(
            session=db_session,
            label=AnnotationLabelCreate(
                dataset_id=collection.dataset_id, annotation_label_name="boat"
            ),
        )


def test_create__name_taken_in_other_dataset(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other")
    annotation_label_resolver.create(
        session=db_session,
        label=AnnotationLabelCreate(
            dataset_id=other_collection.dataset_id, annotation_label_name="boat"
        ),
    )

    label = annotation_label_resolver.create(
        session=db_session,
        label=AnnotationLabelCreate(dataset_id=collection.dataset_id, annotation_label_name="boat"),
    )

    assert label.dataset_id == collection.dataset_id
