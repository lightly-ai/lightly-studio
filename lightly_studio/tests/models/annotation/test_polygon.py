"""Tests for polygon validation."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from lightly_studio.models.annotation import polygon


def test_validate_polygons__rounds_then_boxes_outward() -> None:
    result = polygon.validate_polygons(polygons=[[(1.2, 2.7), (10.5, 2.7), (10.5, 8.0001)]])
    assert result.polygons == [[[1.2, 2.7], [10.5, 2.7], [10.5, 8.0]]]
    assert (result.x, result.y, result.width, result.height) == (1, 2, 10, 6)


def test_validate_polygons__rounds_to_millipixel() -> None:
    result = polygon.validate_polygons(polygons=[[(0.12345, 0.0), (1.0, 0.0), (1.0, 1.0)]])
    assert result.polygons[0][0] == [0.123, 0.0]


def test_validate_polygons__box_spans_all_parts() -> None:
    result = polygon.validate_polygons(
        polygons=[[(0, 0), (2, 0), (2, 2)], [(10, 10), (12, 10), (12, 13)]]
    )
    assert (result.x, result.y, result.width, result.height) == (0, 0, 12, 13)


@pytest.mark.parametrize(
    ("polygons", "message"),
    [
        ([], "at least 1 part"),
        ([[(0, 0), (1, 0)]], "at least 3 vertices"),
        ([[(0, 0), (1, float("nan")), (1, 1)]], "finite"),
        ([[(0, 0), (1, float("inf")), (1, 1)]], "finite"),
    ],
)
def test_validate_polygons__invalid(
    polygons: Sequence[Sequence[Sequence[float]]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        polygon.validate_polygons(polygons=polygons)
