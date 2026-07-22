"""Tests for updating the temporal span of an annotation."""

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image


def _create_event_annotation(
    db_session: Session,
    collection_id: UUID,
    start_time_s: float,
    end_time_s: float,
) -> UUID:
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="event"
    )
    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample.png",
    )
    return annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                start_time_s=start_time_s,
                end_time_s=end_time_s,
            )
        ],
    )[0]


def test_update_temporal_span(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    annotation_id = _create_event_annotation(
        db_session, collection_id, start_time_s=1.0, end_time_s=5.0
    )

    annotation = annotation_resolver.update_temporal_span(
        session=db_session,
        annotation_id=annotation_id,
        start_time_s=2.5,
        end_time_s=8.0,
    )

    assert annotation.sample_id == annotation_id
    assert annotation.temporal_span_details is not None
    assert annotation.temporal_span_details.start_time_s == 2.5
    assert annotation.temporal_span_details.end_time_s == 8.0


def test_update_temporal_span__rejects_inverted_span(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    annotation_id = _create_event_annotation(
        db_session, collection_id, start_time_s=1.0, end_time_s=5.0
    )

    with pytest.raises(ValueError, match=r"start_time_s must be less than end_time_s."):
        annotation_resolver.update_temporal_span(
            session=db_session,
            annotation_id=annotation_id,
            start_time_s=6.0,
            end_time_s=5.0,
        )


def test_update_temporal_span__annotation_without_span(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample.png",
    )
    annotation_id = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=10,
                y=10,
                width=20,
                height=20,
            )
        ],
    )[0]

    with pytest.raises(ValueError, match=r"does not have a temporal span"):
        annotation_resolver.update_temporal_span(
            session=db_session,
            annotation_id=annotation_id,
            start_time_s=1.0,
            end_time_s=2.0,
        )
