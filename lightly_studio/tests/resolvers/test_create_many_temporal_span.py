"""Tests for creating annotations with optional temporal spans."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
    AnnotationView,
)
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
)


def test_create_many__classification_with_temporal_span(db_session: Session) -> None:
    """Creating a classification annotation with times stores a temporal span row."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="action",
    )

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                start_time_s=1.5,
                end_time_s=4.0,
            )
        ],
    )

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[image.sample_id],
    )
    assert len(annotations) == 1
    annotation = annotations[0]
    assert annotation.sample_id == annotation_ids[0]
    assert annotation.annotation_type == AnnotationType.CLASSIFICATION
    assert annotation.temporal_span_details is not None
    assert annotation.temporal_span_details.start_time_s == 1.5
    assert annotation.temporal_span_details.end_time_s == 4.0

    view = AnnotationView.from_annotation_table(annotation)
    assert view.temporal_span_details is not None
    assert view.temporal_span_details.start_time_s == 1.5
    assert view.temporal_span_details.end_time_s == 4.0


def test_create_many__temporal_span_rejected_for_non_classification(db_session: Session) -> None:
    """Temporal spans are only allowed on CLASSIFICATION annotations."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="object",
    )

    with pytest.raises(ValueError, match="only supported for CLASSIFICATION"):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=image.sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    x=0,
                    y=0,
                    width=10,
                    height=10,
                    start_time_s=0.0,
                    end_time_s=1.0,
                )
            ],
        )


@pytest.mark.parametrize(
    ("start_time_s", "end_time_s", "error_match"),
    [
        (1.0, None, "Missing start_time_s or end_time_s"),
        (None, 2.0, "Missing start_time_s or end_time_s"),
        (-1.0, 2.0, "start_time_s must be non-negative"),
        (3.0, 2.0, "start_time_s must be less than end_time_s"),
    ],
)
def test_create_many__invalid_temporal_span(
    db_session: Session,
    start_time_s: float | None,
    end_time_s: float | None,
    error_match: str,
) -> None:
    """Invalid temporal span input is rejected."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="action",
    )

    with pytest.raises(ValueError, match=error_match):
        annotation_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=image.sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.CLASSIFICATION,
                    start_time_s=start_time_s,
                    end_time_s=end_time_s,
                )
            ],
        )


def test_delete_annotation__removes_temporal_span(db_session: Session) -> None:
    """Deleting an annotation also deletes its temporal span row."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="action",
    )

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                start_time_s=0.0,
                end_time_s=1.0,
            )
        ],
    )
    annotation_id = annotation_ids[0]

    annotation_resolver.delete_annotation(session=db_session, annotation_id=annotation_id)

    assert db_session.get(TemporalSpanTable, annotation_id) is None, (
        "Temporal span row should be deleted with the annotation."
    )
