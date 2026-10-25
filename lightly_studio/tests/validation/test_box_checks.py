"""Tests for object-detection box integrity checks."""

from __future__ import annotations

from uuid import uuid4

from lightly_studio.evaluation.object_detection_metric import BoundingBox
from lightly_studio.validation import box_checks


def _box(x: int, y: int, width: int, height: int) -> BoundingBox:
    return BoundingBox(
        annotation_id=uuid4(), x=x, y=y, width=width, height=height, label_id=uuid4()
    )


def test_find_degenerate_boxes() -> None:
    ok = _box(x=0, y=0, width=10, height=10)
    zero_width = _box(x=0, y=0, width=0, height=10)
    negative_height = _box(x=0, y=0, width=10, height=-5)

    result = box_checks.find_degenerate_boxes([ok, zero_width, negative_height])

    assert result == [zero_width.annotation_id, negative_height.annotation_id]


def test_find_degenerate_boxes__empty() -> None:
    assert box_checks.find_degenerate_boxes([]) == []


def test_find_out_of_bounds_boxes() -> None:
    inside = _box(x=0, y=0, width=10, height=10)
    on_edge = _box(x=90, y=90, width=10, height=10)  # x + width == image width -> in bounds
    negative_x = _box(x=-1, y=0, width=10, height=10)
    past_right = _box(x=95, y=0, width=10, height=10)  # 95 + 10 = 105 > 100
    past_bottom = _box(x=0, y=95, width=10, height=10)

    result = box_checks.find_out_of_bounds_boxes(
        [inside, on_edge, negative_x, past_right, past_bottom],
        image_width=100,
        image_height=100,
    )

    assert result == [negative_x.annotation_id, past_right.annotation_id, past_bottom.annotation_id]


def test_find_out_of_bounds_boxes__empty() -> None:
    assert box_checks.find_out_of_bounds_boxes([], image_width=100, image_height=100) == []
