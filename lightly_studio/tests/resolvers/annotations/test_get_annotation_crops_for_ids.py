from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


@pytest.mark.parametrize(
    "annotation_type",
    [AnnotationType.OBJECT_DETECTION, AnnotationType.SEGMENTATION_MASK],
)
def test_get_annotation_crops_for_ids__clamps_box_to_image_bounds(
    db_session: Session,
    annotation_type: AnnotationType,
) -> None:
    """Boxes extending outside the image are clamped, for either detail table."""
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
        width=100,
        height=100,
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=annotation_type,
        annotation_data={"x": -10, "y": -5, "width": 50, "height": 120},
    )

    result = annotation_resolver.get_annotation_crops_for_ids(
        session=db_session,
        annotation_sample_ids=[annotation.sample_id],
    )

    assert [crop.annotation_sample_id for crop in result] == [annotation.sample_id]
    assert [crop.image_crop for crop in result] == [
        ImageCrop(filepath="/path/to/sample.png", x=0, y=0, width=40, height=100)
    ]


def test_get_annotation_crops_for_ids__skips_invalid_boxes(
    db_session: Session,
) -> None:
    """Annotations whose box does not overlap the image are omitted from the result."""
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
        width=100,
        height=100,
    )
    valid_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 10, "y": 10, "width": 20, "height": 20},
    )
    invalid_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 200, "y": 200, "width": 20, "height": 20},
    )

    result = annotation_resolver.get_annotation_crops_for_ids(
        session=db_session,
        annotation_sample_ids=[valid_annotation.sample_id, invalid_annotation.sample_id],
    )

    assert [crop.annotation_sample_id for crop in result] == [valid_annotation.sample_id]
    assert len(result) == 1


def test_get_annotation_crops_for_ids__empty_input(
    db_session: Session,
) -> None:
    """An empty input list returns an empty list."""
    result = annotation_resolver.get_annotation_crops_for_ids(
        session=db_session,
        annotation_sample_ids=[],
    )

    assert result == []


def test_get_annotation_crops_for_ids__unknown_ids(
    db_session: Session,
) -> None:
    """Unknown annotation IDs are ignored."""
    result = annotation_resolver.get_annotation_crops_for_ids(
        session=db_session,
        annotation_sample_ids=[uuid4()],
    )

    assert result == []
