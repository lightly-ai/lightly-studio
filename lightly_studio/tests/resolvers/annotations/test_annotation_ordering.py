"""Tests for the shared annotation ordering helper."""

from __future__ import annotations

import pytest
from sqlmodel import col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.annotations import annotation_ordering


def test_build_order_by() -> None:
    order_by = annotation_ordering.build_order_by(
        file_path_abs=col(ImageTable.file_path_abs),
        created_at=col(AnnotationBaseTable.created_at),
        annotation_sample_id=col(AnnotationBaseTable.sample_id),
    )

    assert [str(clause) for clause in order_by] == [
        "image.file_path_abs ASC",
        "annotation_base.created_at ASC",
        "annotation_base.sample_id ASC",
    ]


def test_build_order_by__leading_order_key_comes_first() -> None:
    order_by = annotation_ordering.build_order_by(
        file_path_abs=col(ImageTable.file_path_abs),
        created_at=col(AnnotationBaseTable.created_at),
        annotation_sample_id=col(AnnotationBaseTable.sample_id),
        leading_order_key=col(AnnotationBaseTable.confidence).desc(),
    )

    assert [str(clause) for clause in order_by] == [
        "annotation_base.confidence DESC",
        "image.file_path_abs ASC",
        "annotation_base.created_at ASC",
        "annotation_base.sample_id ASC",
    ]


@pytest.mark.parametrize(
    ("sample_type", "expected"),
    [
        (SampleType.IMAGE, col(ImageTable.file_path_abs)),
        (SampleType.VIDEO, col(VideoTable.file_path_abs)),
        (SampleType.VIDEO_FRAME, col(VideoTable.file_path_abs)),
    ],
)
def test_file_path_abs_expression(sample_type: SampleType, expected: object) -> None:
    expression = annotation_ordering.file_path_abs_expression(sample_type=sample_type)

    assert str(expression) == str(expected)


def test_file_path_abs_expression__unsupported_sample_type() -> None:
    with pytest.raises(NotImplementedError, match="Unsupported sample type"):
        annotation_ordering.file_path_abs_expression(sample_type=SampleType.GROUP)


def test_coalesced_file_path_abs_expression() -> None:
    expression = annotation_ordering.coalesced_file_path_abs_expression()

    assert str(expression) == "coalesce(image.file_path_abs, video.file_path_abs, :coalesce_1)"
