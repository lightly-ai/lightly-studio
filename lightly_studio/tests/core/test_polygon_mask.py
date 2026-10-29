from __future__ import annotations

import numpy as np
import pytest
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from numpy.typing import NDArray

from lightly_studio.core import polygon_mask

# The expected masks are from pycocotools: decode(merge(frPyObjects(polygons, height, width))).


def test_polygons_to_rle() -> None:
    rle = polygon_mask.polygons_to_rle(
        polygons=[[(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)]], width=5, height=4
    )

    assert rle == [6, 2, 3, 2, 7]
    expected_mask = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    np.testing.assert_array_equal(_decode(rle=rle, width=5, height=4), np.array(expected_mask))


def test_polygons_to_rle__triangle() -> None:
    rle = polygon_mask.polygons_to_rle(
        polygons=[[(1.0, 1.0), (6.0, 1.0), (1.0, 5.0)]], width=8, height=7
    )

    expected_mask = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 0, 0, 0],
        [0, 1, 1, 1, 0, 0, 0, 0],
        [0, 1, 1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]
    np.testing.assert_array_equal(_decode(rle=rle, width=8, height=7), np.array(expected_mask))


def test_polygons_to_rle__overlapping_polygons() -> None:
    rle = polygon_mask.polygons_to_rle(
        polygons=[
            [(0.5, 0.5), (2.5, 0.5), (2.5, 2.5), (0.5, 2.5)],
            [(1.5, 1.5), (3.5, 1.5), (3.5, 3.5), (1.5, 3.5)],
        ],
        width=5,
        height=5,
    )

    expected_mask = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ]
    np.testing.assert_array_equal(_decode(rle=rle, width=5, height=5), np.array(expected_mask))


def test_polygons_to_rle__mask_starts_and_ends_with_one_pixel() -> None:
    # The polygons go past the image borders at the top left and at the bottom right.
    rle = polygon_mask.polygons_to_rle(
        polygons=[
            [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)],
            [(3.0, 2.0), (5.0, 2.0), (5.0, 4.0), (3.0, 4.0)],
        ],
        width=4,
        height=3,
    )

    assert rle == [0, 1, 10, 1]


def test_polygons_to_rle__polygon_outside_of_image() -> None:
    rle = polygon_mask.polygons_to_rle(
        polygons=[[(-5.0, -5.0), (-2.0, -5.0), (-2.0, -2.0)]], width=4, height=3
    )

    assert rle == [12]


@pytest.mark.parametrize(
    "polygon",
    [
        [],
        [(1.0, 1.0)],
        [(1.0, 1.0), (3.0, 2.0)],
    ],
)
def test_polygons_to_rle__polygon_without_area(polygon: list[tuple[float, float]]) -> None:
    rle = polygon_mask.polygons_to_rle(polygons=[polygon], width=4, height=3)

    assert rle == [12]


def test_polygons_to_rle__no_polygons() -> None:
    rle = polygon_mask.polygons_to_rle(polygons=[], width=4, height=3)

    assert rle == [12]


def _decode(rle: list[int], width: int, height: int) -> NDArray[np.int_]:
    return BinaryMaskSegmentation.from_rle(
        rle_row_wise=rle, width=width, height=height
    ).get_binary_mask()
