"""Tests for annotation_label_resolver.update resolver."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_update(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )

    updated = annotation_label_resolver.update(
        session=db_session,
        label_id=label.annotation_label_id,
        label_data=AnnotationLabelCreate(
            dataset_id=collection.dataset_id, annotation_label_name="ship"
        ),
    )

    assert updated is not None
    assert updated.annotation_label_name == "ship"


def test_update__label_with_annotation(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    updated = annotation_label_resolver.update(
        session=db_session,
        label_id=label.annotation_label_id,
        label_data=AnnotationLabelCreate(
            dataset_id=collection.dataset_id, annotation_label_name="ship"
        ),
    )

    assert updated is not None
    assert updated.annotation_label_name == "ship"
    db_session.refresh(annotation)
    assert annotation.annotation_label_id == label.annotation_label_id


def test_update__same_name(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )

    updated = annotation_label_resolver.update(
        session=db_session,
        label_id=label.annotation_label_id,
        label_data=AnnotationLabelCreate(
            dataset_id=collection.dataset_id, annotation_label_name="boat"
        ),
    )

    assert updated is not None
    assert updated.annotation_label_name == "boat"


def test_update__name_taken(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )
    create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="ship"
    )

    with pytest.raises(IntegrityError, match="Annotation label already exists"):
        annotation_label_resolver.update(
            session=db_session,
            label_id=label.annotation_label_id,
            label_data=AnnotationLabelCreate(
                dataset_id=collection.dataset_id, annotation_label_name="ship"
            ),
        )


def test_update__name_taken_in_other_dataset(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other")
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )
    create_annotation_label(
        session=db_session, root_collection_id=other_collection.collection_id, label_name="ship"
    )

    updated = annotation_label_resolver.update(
        session=db_session,
        label_id=label.annotation_label_id,
        label_data=AnnotationLabelCreate(
            dataset_id=collection.dataset_id, annotation_label_name="ship"
        ),
    )

    assert updated is not None
    assert updated.annotation_label_name == "ship"


def test_update__unknown_label(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    updated = annotation_label_resolver.update(
        session=db_session,
        label_id=uuid4(),
        label_data=AnnotationLabelCreate(
            dataset_id=collection.dataset_id, annotation_label_name="ship"
        ),
    )

    assert updated is None


def test_update__keeps_color(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="boat"
    )
    annotation_label_resolver.set_color(
        session=db_session, label_id=label.annotation_label_id, color="#ff0000", alpha=0.5
    )

    updated = annotation_label_resolver.update(
        session=db_session,
        label_id=label.annotation_label_id,
        label_data=AnnotationLabelCreate(
            dataset_id=collection.dataset_id, annotation_label_name="ship"
        ),
    )

    assert updated is not None
    assert updated.annotation_label_name == "ship"
    assert updated.color == "#ff0000"
    assert updated.alpha == 0.5
