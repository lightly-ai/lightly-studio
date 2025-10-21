"""Tests for annotation filtering functionality."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers import annotation_resolver as annotations_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.helpers_resolvers import (
    create_annotation_label,
    create_dataset,
    create_sample,
    create_tag,
)


@pytest.fixture
def filter_test_data(
    test_db: Session,
) -> tuple[AnnotationBaseTable, AnnotationBaseTable]:
    """Create test data for filter tests."""
    # Create datasets
    dataset1 = create_dataset(session=test_db)
    dataset2 = create_dataset(session=test_db, dataset_name="dataset2")

    # Create samples
    sample1 = create_sample(
        session=test_db, dataset_id=dataset1.dataset_id, file_path_abs="/path/to/sample1.png"
    )
    sample2 = create_sample(
        session=test_db, dataset_id=dataset2.dataset_id, file_path_abs="/path/to/sample2.png"
    )

    # Create labels
    label1 = create_annotation_label(session=test_db, annotation_label_name="label1")
    label2 = create_annotation_label(session=test_db, annotation_label_name="label2")

    # Create tags
    tag1 = create_tag(session=test_db, dataset_id=dataset1.dataset_id, tag_name="tag1")
    tag2 = create_tag(session=test_db, dataset_id=dataset2.dataset_id, tag_name="tag2")

    # Create annotations
    annotation_ids = annotation_resolver.create_many(
        session=test_db,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label1.annotation_label_id,
                dataset_id=dataset1.dataset_id,
                sample_id=sample1.sample_id,
                annotation_type="object_detection",
                x=0,
                y=0,
                width=100,
                height=100,
            ),
            AnnotationCreate(
                annotation_label_id=label2.annotation_label_id,
                dataset_id=dataset2.dataset_id,
                sample_id=sample2.sample_id,
                annotation_type="semantic_segmentation",
            ),
        ],
    )
    assert len(annotation_ids) == 2
    annotations = annotation_resolver.get_by_ids(session=test_db, annotation_ids=annotation_ids)
    annotation1, annotation2 = annotations
    # Add tags to annotations
    annotation1.tags.append(tag1)
    annotation2.tags.append(tag2)
    test_db.commit()

    return annotation1, annotation2


def test_filter_by_dataset(
    test_db: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by dataset."""
    annotation1, _ = filter_test_data

    # Test filtering by dataset
    dataset_filter = AnnotationsFilter(dataset_ids=[annotation1.dataset_id])
    filtered_annotations = annotations_resolver.get_all(
        session=test_db, filters=dataset_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].dataset_id == annotation1.dataset_id


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
    assert filtered_annotations[0].annotation_id == annotation1.annotation_id


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
        dataset_ids=[annotation1.dataset_id],
        annotation_label_ids=[annotation1.annotation_label_id],
        annotation_tag_ids=[annotation1.tags[0].tag_id],
    )
    filtered_annotations = annotations_resolver.get_all(
        session=test_db, filters=combined_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].annotation_id == annotation1.annotation_id
