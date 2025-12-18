"""Tests for annotation_label_resolver.get_by_label_name resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import create_dataset, create_annotation_label
from tests.conftest import AnnotationsTestData

def test_get_by_label_name__returns_label(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test getting annotations by label name."""
    dataset_id_1 = create_dataset(session=db_session).dataset_id
    dataset_id_2 = create_dataset(session=db_session, dataset_name="ds2").dataset_id
    label_1 = create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id_1,
        label_name="cat",
    )
    create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id_1,
        label_name="dog",
    )
    create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id_2,
        label_name="bird",
    )

    annotation_label = annotation_label_resolver.get_by_label_name(
        session=db_session,
        root_dataset_id=dataset_id_1,
        label_name="cat",
    )
    assert annotation_label == label_1

def test_get_by_label_name__returns_none(
    db_session: Session,
) -> None:
    """Test returning None for a nonexistent label."""
    dataset_id_1 = create_dataset(session=db_session).dataset_id
    dataset_id_2 = create_dataset(session=db_session, dataset_name="ds2").dataset_id
    label_1 = create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id_1,
        label_name="cat",
    )
    create_annotation_label(
        session=db_session,
        root_dataset_id=dataset_id_1,
        label_name="dog",
    )

    assert annotation_label_resolver.get_by_label_name(
        session=db_session,
        root_dataset_id=dataset_id_1,
        label_name="nonexistent_label_name",
    ) is None
    assert annotation_label_resolver.get_by_label_name(
        session=db_session,
        root_dataset_id=dataset_id_2,
        label_name="cat",
    ) is None
