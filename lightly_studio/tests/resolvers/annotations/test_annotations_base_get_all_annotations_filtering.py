"""Tests for the AnnotationsFilter class."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import annotation_resolver as annotations_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


def test_filter_by_collection_ids(
    db_session: Session,
    collections: list[CollectionTable],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test filtering annotations by collection ids."""
    # We have 9 annotations all together.
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            collection_ids=[
                child.collection_id for collection in collections for child in collection.children
            ]
        ),
    ).annotations

    assert len(annotations) == 9

    # We have 6 annotations for the first collection.
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(collection_ids=[collections[0].children[0].collection_id]),
    ).annotations
    assert len(annotations) == 6

    # We have 3 annotations for the second.
    annotations = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(collection_ids=[collections[1].children[0].collection_id]),
    ).annotations
    assert len(annotations) == 3

    # The third collection has no annotations - no annotation children collections.
    assert len(collections[2].children) == 0


def test_filter_by_annotation_label_ids(
    db_session: Session,
    annotation_labels: list[AnnotationLabelTable],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    # We have 9 annotations all together
    annotations_all = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            annotation_label_ids=[label.annotation_label_id for label in annotation_labels]
        ),
    ).annotations
    assert len(annotations_all) == 9

    # We have 6 annotations for the first label
    annotations_label_0 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_label_ids=[annotation_labels[0].annotation_label_id]),
    ).annotations
    assert len(annotations_label_0) == 6

    # We have 3 annotations for the second label
    annotations_label_1 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(annotation_label_ids=[annotation_labels[1].annotation_label_id]),
    ).annotations
    assert len(annotations_label_1) == 3


def test_filter_by_annotation_tag_ids(
    db_session: Session,
    annotation_tags_assigned: list[TagTable],
) -> None:
    # Check that we have 2 annotations with the first tag
    assert (
        len(
            annotations_resolver.get_all(
                db_session,
                filters=AnnotationsFilter(tag_ids=[annotation_tags_assigned[0].tag_id]),
            ).annotations
        )
        == 2
    )

    # Check that we have 3 annotations with the second tag
    assert (
        len(
            annotations_resolver.get_all(
                db_session,
                filters=AnnotationsFilter(tag_ids=[annotation_tags_assigned[1].tag_id]),
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
                    tag_ids=[
                        annotation_tags_assigned[0].tag_id,
                        annotation_tags_assigned[1].tag_id,
                    ]
                ),
            ).annotations
        )
        == 5
    )


def test_annotations_pagination_without_filters(
    db_session: Session,
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test pagination parameters."""
    # We have 9 annotations all together
    annotations_all = annotations_resolver.get_all(
        db_session,
        pagination=Paginated(
            offset=0,
            limit=100,
        ),
    ).annotations
    assert len(annotations_all) == 9

    # Pagination with offset and limit
    page_1 = annotations_resolver.get_all(
        db_session,
        pagination=Paginated(
            offset=0,
            limit=5,
        ),
    ).annotations
    assert len(page_1) == 5

    page_2 = annotations_resolver.get_all(
        db_session,
        pagination=Paginated(
            offset=5,
            limit=5,
        ),
    ).annotations
    assert len(page_2) == 4


def test_annotations_pagination_with_filters(
    db_session: Session,
    collections: list[CollectionTable],
    annotation_labels: list[AnnotationLabelTable],
    annotations_test_data: None,  # noqa: ARG001
) -> None:
    """Test pagination parameters with filters."""
    annotations_all = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            collection_ids=[collections[0].children[0].collection_id],
            annotation_label_ids=[annotation_labels[0].annotation_label_id],
        ),
        pagination=Paginated(
            offset=0,
            limit=10,
        ),
    ).annotations
    assert len(annotations_all) == 6

    annotations_page_1 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            collection_ids=[collections[0].children[0].collection_id],
            annotation_label_ids=[annotation_labels[0].annotation_label_id],
        ),
        pagination=Paginated(
            offset=0,
            limit=4,
        ),
    ).annotations
    assert len(annotations_page_1) == 4

    annotations_page_2 = annotations_resolver.get_all(
        db_session,
        filters=AnnotationsFilter(
            collection_ids=[collections[0].children[0].collection_id],
            annotation_label_ids=[annotation_labels[0].annotation_label_id],
        ),
        pagination=Paginated(
            offset=4,
            limit=4,
        ),
    ).annotations
    assert len(annotations_page_2) == 2
