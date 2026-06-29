from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image


def test_create_many__rejects_polygon_with_less_than_three_points(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotation_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="triangle",
    )

    with pytest.raises(ValueError, match="Polygon must have at least 3 points"):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=image.sample_id,
                    annotation_label_id=annotation_label.annotation_label_id,
                    annotation_type=AnnotationType.POLYGON,
                    points=[[10, 20], [30, 40]],
                )
            ],
        )


def test_create_many__rejects_polygon_with_malformed_points(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotation_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="triangle",
    )

    with pytest.raises(
        ValueError,
        match="Polygon point at index 1 must contain exactly 2 coordinates",
    ):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=image.sample_id,
                    annotation_label_id=annotation_label.annotation_label_id,
                    annotation_type=AnnotationType.POLYGON,
                    points=[[10, 20], [30], [40, 50]],
                )
            ],
        )
