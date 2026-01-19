"""Tests for annotation filtering functionality."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers import annotation_resolver as annotations_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


@pytest.fixture
def filter_test_data(
    test_db: Session,
) -> tuple[AnnotationBaseTable, AnnotationBaseTable]:
    """Create test data for filter tests."""
    # Create collections
    collection1 = create_collection(session=test_db)
    collection2 = create_collection(session=test_db, collection_name="collection2")

    # Create samples
    image1 = create_image(
        session=test_db,
        collection_id=collection1.collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=test_db,
        collection_id=collection2.collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    # Create labels
    label1 = create_annotation_label(
        session=test_db, dataset_id=collection1.collection_id, label_name="label1"
    )
    label2 = create_annotation_label(
        session=test_db, dataset_id=collection2.collection_id, label_name="label2"
    )

    # Create tags
    tag1 = create_tag(session=test_db, collection_id=collection1.collection_id, tag_name="tag1")
    tag2 = create_tag(session=test_db, collection_id=collection2.collection_id, tag_name="tag2")

    # Create annotations for collection1
    annotation1_id = annotation_resolver.create_many(
        session=test_db,
        parent_collection_id=collection1.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label1.annotation_label_id,
                parent_sample_id=image1.sample_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=0,
                y=0,
                width=100,
                height=100,
            )
        ],
    )[0]
    # Create annotations for collection2
    annotation2_id = annotation_resolver.create_many(
        session=test_db,
        parent_collection_id=collection2.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label2.annotation_label_id,
                parent_sample_id=image2.sample_id,
                annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
                segmentation_mask=[1, 2, 3, 4, 5],
                x=0,
                y=0,
                width=100,
                height=100,
            ),
        ],
    )[0]
    annotation1 = annotation_resolver.get_by_id(session=test_db, annotation_id=annotation1_id)
    assert annotation1
    annotation2 = annotation_resolver.get_by_id(session=test_db, annotation_id=annotation2_id)
    assert annotation2

    # Add tags to annotations
    annotation1.tags.append(tag1)
    annotation2.tags.append(tag2)
    test_db.commit()

    return annotation1, annotation2


def test_filter_by_collection(
    test_db: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by collection."""
    annotation1, _ = filter_test_data

    # Test filtering by collection
    collection_filter = AnnotationsFilter(collection_ids=[annotation1.sample.collection_id])
    filtered_annotations = annotations_resolver.get_all(
        session=test_db, filters=collection_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample.collection_id == annotation1.sample.collection_id


def test_filter_by_label(
    test_db: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by label."""
    annotation1, _ = filter_test_data

    # Test filtering by label
    label_filter = AnnotationsFilter(annotation_label_ids=[annotation1.annotation_label_id])
    filtered_annotations = annotations_resolver.get_all(
        session=test_db, filters=label_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].annotation_label_id == annotation1.annotation_label_id


def test_filter_by_tag(
    test_db: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by tag."""
    annotation1, _ = filter_test_data

    # Test filtering by tag
    tag_filter = AnnotationsFilter(annotation_tag_ids=[annotation1.tags[0].tag_id])
    filtered_annotations = annotations_resolver.get_all(
        session=test_db, filters=tag_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample_id == annotation1.sample_id


def test_pagination(
    test_db: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],  # noqa: ARG001
) -> None:
    """Test pagination of annotations."""
    # Test pagination
    pagination = Paginated(offset=0, limit=1)
    paginated_annotations = annotations_resolver.get_all(
        session=test_db, pagination=pagination
    ).annotations
    assert len(paginated_annotations) == 1


def test_combined_filters(
    test_db: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test combining multiple filters."""
    annotation1, _ = filter_test_data

    # Test combined filters
    combined_filter = AnnotationsFilter(
        collection_ids=[annotation1.sample.collection_id],
        annotation_label_ids=[annotation1.annotation_label_id],
        annotation_tag_ids=[annotation1.tags[0].tag_id],
    )
    filtered_annotations = annotations_resolver.get_all(
        session=test_db, filters=combined_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample_id == annotation1.sample_id
