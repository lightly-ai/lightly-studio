"""Tests for the AnnotationsFilter class."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import annotation_resolver as annotations_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


def test_filter_by_dataset_ids(
    db_session: Session,
    datasets: list[DatasetTable],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test that object detection details are correctly loaded."""
    # We have 12 annotations all together
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(dataset_ids=[dataset.dataset_id for dataset in datasets]),
    ).annotations

    assert len(annotations) == 12

    # We have 8 annotations for the first dataset
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(dataset_ids=[datasets[0].dataset_id]),
    ).annotations
    assert len(annotations) == 8

    # We have 4 annotations for the second
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(dataset_ids=[datasets[1].dataset_id]),
    ).annotations
    assert len(annotations) == 4

    # the third dataset has no annotations
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(dataset_ids=[datasets[2].dataset_id]),
    ).annotations
    assert len(annotations) == 0


def test_filter_by_annotation_label_ids(
    db_session: Session,
    annotation_labels: list[AnnotationLabelTable],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    # We have 12 annotations all together
    annotations_all = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            annotation_label_ids=[label.annotation_label_id for label in annotation_labels]
        ),
    ).annotations
    assert len(annotations_all) == 12

    # We have 8 annotations for the first dataset
    annotations_label_0 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_label_ids=[annotation_labels[0].annotation_label_id]),
    ).annotations
    assert len(annotations_label_0) == 8

    # We have 4 annotations for the second
    annotations_label_1 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_label_ids=[annotation_labels[1].annotation_label_id]),
    ).annotations
    assert len(annotations_label_1) == 4


def test_filter_by_annotation_tag_ids(
    db_session: Session,
    annotation_tags_assigned: list[TagTable],
) -> None:
    # Check that we have 2 annotations with the first tag
    assert (
        len(
            annotations_resolver.get_all(
                db_session,
                filters=AnnotationsFilter(annotation_tag_ids=[annotation_tags_assigned[0].tag_id]),
            ).annotations
        )
        == 2
    )

    # Check that we have 3 annotations with the second tag
    assert (
        len(
            annotations_resolver.get_all(
                db_session,
                filters=AnnotationsFilter(annotation_tag_ids=[annotation_tags_assigned[1].tag_id]),
            ).annotations
        )
        == 3
    )

    # Check that we have 5 annotations with both tags
    assert (
        len(
            annotations_resolver.get_all(
                db_session,
                filters=AnnotationsFilter(
                    annotation_tag_ids=[
                        annotation_tags_assigned[0].tag_id,
                        annotation_tags_assigned[1].tag_id,
                    ]
                ),
            ).annotations
        )
        == 5
    )


def test_filter_by_sample_tag_ids(
    db_session: Session,
    samples_assigned_with_tags: tuple[list[ImageTable], list[TagTable]],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    # We have 12 annotations all together
    annotations_all = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            sample_tag_ids=[sample.tags[0].tag_id for sample in samples_assigned_with_tags[0]]
        ),
    ).annotations
    assert len(annotations_all) == 12

    # We have 8 annotations for the first tag
    annotations_tag_0 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(sample_tag_ids=[samples_assigned_with_tags[0][0].tags[0].tag_id]),
    ).annotations
    assert len(annotations_tag_0) == 8

    # We have 4 annotations for the second tag
    annotations_tag_1 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(sample_tag_ids=[samples_assigned_with_tags[0][1].tags[0].tag_id]),
    ).annotations
    assert len(annotations_tag_1) == 4


def test_annotations_pagination_without_filters(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test pagination parameters."""
    # We have 12 annotations all together
    annotations_all = annotations_resolver.get_all(
        db_session,
        pagination=Paginated(
            offset=0,
            limit=100,
        ),
    ).annotations
    assert len(annotations_all) == 12

    # Pagination with offset and limit
    page_1 = annotations_resolver.get_all(
        db_session,
        pagination=Paginated(
            offset=0,
            limit=10,
        ),
    ).annotations
    assert len(page_1) == 10

    page_2 = annotations_resolver.get_all(
        db_session,
        pagination=Paginated(
            offset=10,
            limit=10,
        ),
    ).annotations
    assert len(page_2) == 2


def test_annotations_pagination_with_filters(
    db_session: Session,
    datasets: list[DatasetTable],
    annotation_labels: list[AnnotationLabelTable],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test pagination parameters with filters."""
    annotations_all = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            dataset_ids=[datasets[0].dataset_id],
            annotation_label_ids=[annotation_labels[0].annotation_label_id],
        ),
        pagination=Paginated(
            offset=0,
            limit=10,
        ),
    ).annotations
    assert len(annotations_all) == 8

    annotations_page_1 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            dataset_ids=[datasets[0].dataset_id],
            annotation_label_ids=[annotation_labels[0].annotation_label_id],
        ),
        pagination=Paginated(
            offset=0,
            limit=6,
        ),
    ).annotations
    assert len(annotations_page_1) == 6

    annotations_page_2 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            dataset_ids=[datasets[0].dataset_id],
            annotation_label_ids=[annotation_labels[0].annotation_label_id],
        ),
        pagination=Paginated(
            offset=6,
            limit=6,
        ),
    ).annotations
    assert len(annotations_page_2) == 2
