"""Tests for get_all_by_parent_sample_ids resolver."""

from __future__ import annotations

import uuid

from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_get_all_by_parent_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="label",
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_b.png",
    )
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_a.png",
    )

    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=label.annotation_label_id,
            ),
        ],
    )
    image_b_annotations = [
        annotation for annotation in annotations if annotation.parent_sample_id == image_b.sample_id
    ]

    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[
            image_b.sample_id,
        ],
    )
    assert len(result) == 2
    assert [annotation.sample_id for annotation in result] == [
        image_b_annotations[0].sample_id,
        image_b_annotations[1].sample_id,
    ]


def test_get_all_by_parent_sample_ids_with_no_parent_sample_ids_returns_empty_result(
    db_session: Session,
) -> None:
    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[]
    )

    assert result == []


def test_get_all_by_parent_sample_ids__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More ids than PostgreSQL's 65,535-parameter cap.
    result = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[uuid.uuid4() for _ in range(70_000)]
    )

    assert result == []
