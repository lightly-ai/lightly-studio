"""Tests for get_all_by_collection_id_and_parent_sample_ids resolver."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_all_by_collection_id_and_parent_sample_ids__filters_by_annotation_type(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    od_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    result = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=od_annotation.sample.collection_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    assert [annotation.sample_id for annotation in result] == [od_annotation.sample_id]


def test_get_all_by_collection_id_and_parent_sample_ids__filters_by_annotation_collection_id(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotation_in_gt = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
    )

    result = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=annotation_in_gt.sample.collection_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    assert [annotation.sample_id for annotation in result] == [annotation_in_gt.sample_id]


def test_get_all_by_collection_id_and_parent_sample_ids__eager_loads_object_detection_details(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    db_session.expire_all()

    result = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=annotation.sample.collection_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    assert len(result) == 1
    # Without joinedload, the relationship would be in `unloaded` until accessed.
    state = inspect(result[0])
    assert state is not None
    assert "object_detection_details" not in state.unloaded
