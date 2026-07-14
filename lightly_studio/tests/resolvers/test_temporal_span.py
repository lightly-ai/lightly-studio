"""Tests for temporal span validation when creating annotations."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
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
