"""Tests for dataset object-detection annotation validation."""

from __future__ import annotations

from uuid import UUID

import pytest

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_validate__flags_degenerate_and_out_of_bounds_boxes(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Flags boxes with a bad size or outside the image, and leaves valid boxes alone."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(
        session=dataset.session, collection_id=dataset.collection_id, width=100, height=100
    )
    create_collection(
        session=dataset.session,
        collection_name="predictions",
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    def _annotate(annotation_data: dict[str, int]) -> UUID:
        annotation = create_annotation(
            session=dataset.session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_data=annotation_data,
            annotation_collection_name="predictions",
        )
        return annotation.sample_id

    _annotate({"x": 0, "y": 0, "width": 10, "height": 10})  # valid
    degenerate_id = _annotate({"x": 0, "y": 0, "width": 0, "height": 10})  # zero width
    out_of_bounds_id = _annotate({"x": 95, "y": 0, "width": 10, "height": 10})  # 95 + 10 > 100

    report = dataset.validate(annotation_source="predictions")

    assert [issue.annotation_id for issue in report.degenerate_boxes] == [degenerate_id]
    assert [issue.annotation_id for issue in report.out_of_bounds_boxes] == [out_of_bounds_id]
    flagged = report.degenerate_boxes + report.out_of_bounds_boxes
    assert all(issue.sample_id == image.sample_id for issue in flagged)


def test_validate__clean_dataset_has_no_issues(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """A dataset with only valid boxes produces an empty report."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(
        session=dataset.session, collection_id=dataset.collection_id, width=100, height=100
    )
    create_collection(
        session=dataset.session,
        collection_name="predictions",
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
        annotation_collection_name="predictions",
    )

    report = dataset.validate(annotation_source="predictions")

    assert report.degenerate_boxes == []
    assert report.out_of_bounds_boxes == []


def test_validate__unknown_source_raises(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises ValueError when the annotation source does not exist."""
    dataset = ImageDataset.create(name="test_dataset")

    with pytest.raises(ValueError, match="not found"):
        dataset.validate(annotation_source="missing")
