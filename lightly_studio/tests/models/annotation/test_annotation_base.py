"""Tests for the annotation base models."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType, AnnotationView
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


class TestAnnotationView:
    def test_from_annotation_table__skips_polygon_details_of_other_types(
        self, db_session: Session
    ) -> None:
        collection = create_collection(session=db_session)
        image = create_image(session=db_session, collection_id=collection.collection_id)
        label = create_annotation_label(
            session=db_session, root_collection_id=collection.collection_id
        )
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        db_session.expire(annotation, ["polygon_details"])

        view = AnnotationView.from_annotation_table(annotation=annotation)

        assert view.polygon_details is None
        assert "polygon_details" in inspect(annotation, raiseerr=True).unloaded
