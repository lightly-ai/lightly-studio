"""Tests for semantic segmentation resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


def test_delete_annotations(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test deleting annotations."""
    # get a label ID to create filters
    label = annotation_label_resolver.get_by_label_name(
        session=db_session, label_name="test_label_0"
    )
    assert label is not None
    annotation_filter = AnnotationsFilter(annotation_label_ids=[label.annotation_label_id])
    filtered_annotations = annotation_resolver.get_all(
        session=db_session, filters=annotation_filter
    ).annotations
    assert len(filtered_annotations) == 8

    annotation_resolver.delete_annotations(
        session=db_session,
        annotation_label_ids=[label.annotation_label_id],
    )
    filtered_annotations = annotation_resolver.get_all(
        session=db_session, filters=annotation_filter
    ).annotations
    assert len(filtered_annotations) == 0
