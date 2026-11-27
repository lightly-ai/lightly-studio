"""Tests for annotation deletion resolver."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.conftest import AnnotationsTestData


def test_delete_annotations(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test deleting annotations."""
    dataset_id = annotations_test_data.collections[0].dataset_id
    # get a label ID to create filters
    label = annotation_label_resolver.get_by_label_name(
        session=db_session, dataset_id=dataset_id, label_name="test_label_0"
    )
    assert label is not None
    annotation_filter = AnnotationsFilter(annotation_label_ids=[label.annotation_label_id])
    filtered_annotations = annotation_resolver.get_all(
        session=db_session, filters=annotation_filter
    ).annotations
    assert len(filtered_annotations) == 6
    deleted_ids = [annotation.sample_id for annotation in filtered_annotations]
    total_count = annotation_resolver.get_all(session=db_session).total_count

    annotation_resolver.delete_annotations(
        session=db_session,
        annotation_label_ids=[label.annotation_label_id],
    )
    filtered_annotations = annotation_resolver.get_all(
        session=db_session, filters=annotation_filter
    ).annotations
    assert len(filtered_annotations) == 0
    assert all(db_session.get(SampleTable, sample_id) is None for sample_id in deleted_ids)
    assert annotation_resolver.get_all(session=db_session).total_count == total_count - 6


@pytest.mark.usefixtures("annotations_test_data")
def test_delete_annotations__no_label_ids_deletes_nothing(db_session: Session) -> None:
    total_count = annotation_resolver.get_all(session=db_session).total_count
    assert total_count > 0

    annotation_resolver.delete_annotations(session=db_session, annotation_label_ids=[])

    assert annotation_resolver.get_all(session=db_session).total_count == total_count
