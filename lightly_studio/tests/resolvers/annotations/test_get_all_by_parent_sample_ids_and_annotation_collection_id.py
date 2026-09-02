"""Tests for get_all_by_parent_sample_ids_and_annotation_collection_id resolver."""

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


def test_get_all_by_parent_sample_ids_and_annotation_collection_id(
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
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=annotation.sample.collection_id,
    )

    assert [r.sample_id for r in result] == [annotation.sample_id]


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__filters_by_collection(
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

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=annotation_in_gt.sample.collection_id,
    )

    assert [r.sample_id for r in result] == [annotation_in_gt.sample_id]


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__filters_by_parent_sample_id(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="a.png",
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="b.png",
    )
    annotation_a = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image_a.sample_id],
        annotation_collection_id=annotation_a.sample.collection_id,
    )

    assert [r.sample_id for r in result] == [annotation_a.sample_id]


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__empty_parent_sample_ids(
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
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[],
        annotation_collection_id=annotation.sample.collection_id,
    )

    assert result == []


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__eager_loads_sample(
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
    )
    db_session.expire_all()

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=annotation.sample.collection_id,
    )

    assert len(result) == 1
    # Without contains_eager, `sample` would remain in `unloaded` until accessed.
    state = inspect(result[0])
    assert state is not None
    assert "sample" not in state.unloaded


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__annotation_types_none_returns_all(  # noqa: E501
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
    cls_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=od_annotation.sample.collection_id,
        annotation_types=None,
    )

    assert {r.sample_id for r in result} == {
        od_annotation.sample_id,
        cls_annotation.sample_id,
    }


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__annotation_types_single(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    cls_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=cls_annotation.sample.collection_id,
        annotation_types=[AnnotationType.CLASSIFICATION],
    )

    assert [r.sample_id for r in result] == [cls_annotation.sample_id]


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__annotation_types_multiple(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    cls_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )
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
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={"segmentation_mask": [0, 1, 0, 1]},
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=cls_annotation.sample.collection_id,
        annotation_types=[AnnotationType.CLASSIFICATION, AnnotationType.OBJECT_DETECTION],
    )

    assert {r.sample_id for r in result} == {
        cls_annotation.sample_id,
        od_annotation.sample_id,
    }


def test_get_all_by_parent_sample_ids_and_annotation_collection_id__annotation_types_empty_returns_empty(  # noqa: E501
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
    )

    result = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=db_session,
        parent_sample_ids=[image.sample_id],
        annotation_collection_id=annotation.sample.collection_id,
        annotation_types=[],
    )

    assert result == []
