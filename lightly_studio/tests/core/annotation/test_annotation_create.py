from dataclasses import dataclass

import numpy as np
import pytest

from lightly_studio.core.annotation.annotation_create import (
    CreateInstanceSegmentation,
    CreateSemanticSegmentation,
)


@dataclass
class MockImageSample:
    width: int
    height: int


def test_create_instance_segmentation_from_binary_mask() -> None:
    # Create a simple binary mask (10x10) with a 3x2 rectangle on the left side.
    # The rectangle is at rows 2, 3 and 4 and columns 0 and 1 (numbered from 0).
    mask = np.zeros((10, 10), dtype=np.int_)
    mask[2:5, 0:2] = 1

    result = CreateInstanceSegmentation.from_binary_mask(
        label="cat",
        binary_mask=mask,
        confidence=0.9,
    )

    assert result.label == "cat"
    assert result.confidence == pytest.approx(0.9)
    assert result.x == 0
    assert result.y == 2
    assert result.width == 2
    assert result.height == 3
    # RLE for the full 10x10 image:
    # 2 rows of 10 zeros (20) = 20 zeros.
    # 2 ones followed by 8 zeros in row 2.
    # 2 ones followed by 8 zeros in row 3.
    # 2 ones in row 4.
    # 8 zeros in row 4 + 5 rows of 10 zeros (50) = 58 zeros.
    assert result.segmentation_mask == [20, 2, 8, 2, 8, 2, 58]


def test_create_instance_segmentation_from_rle_mask() -> None:
    rle_mask = [20, 2, 8, 2, 8, 2, 58]  # Corresponds to a 3x2 rectangle at (0,2)
    image_sample = MockImageSample(width=10, height=10)

    result = CreateInstanceSegmentation.from_rle_mask(
        label="cat",
        segmentation_mask=rle_mask,
        two_dim_sample=image_sample,
        confidence=0.9,
    )

    assert result.label == "cat"
    assert result.confidence == pytest.approx(0.9)
    assert result.x == 0
    assert result.y == 2
    assert result.width == 2
    assert result.height == 3
    assert result.segmentation_mask == rle_mask


def test_create_semantic_segmentation_from_binary_mask() -> None:
    # Create a simple binary mask (10x10) with a 2x2 square of ones.
    # The square is at rows 2 and 3 and columns 3 and 4 (numbered from 0).
    mask = np.zeros((10, 10), dtype=np.int_)
    mask[2:4, 3:5] = 1

    result = CreateSemanticSegmentation.from_binary_mask(
        label="cat",
        binary_mask=mask,
        confidence=0.9,
    )

    assert result.label == "cat"
    assert result.confidence == pytest.approx(0.9)
    assert result.x == 3
    assert result.y == 2
    assert result.width == 2
    assert result.height == 2
    # RLE for the full 10x10 image:
    # 2 rows of 10 zeros (20) + 3 zeros in row 2 = 23 zeros.
    # 2 ones in row 2.
    # 5 zeros in row 2 + 3 zeros in row 3 = 8 zeros.
    # 2 ones in row 3.
    # 5 zeros in row 3 + 6 rows of 10 zeros (60) = 65 zeros.
    assert result.segmentation_mask == [23, 2, 8, 2, 65]


def test_create_semantic_segmentation_from_binary_mask_empty() -> None:
    mask = np.zeros((10, 10), dtype=np.int_)
    result = CreateSemanticSegmentation.from_binary_mask(
        label="empty",
        binary_mask=mask,
    )

    # The mask is empty.
    assert result.x == 0
    assert result.y == 0
    assert result.width == 0
    assert result.height == 0
    assert result.segmentation_mask == [100]


def test_create_semantic_segmentation_from_rle_mask() -> None:
    rle_mask = [23, 2, 8, 2, 65]  # Corresponds to a 2x2 square at (3,2)
    image_sample = MockImageSample(width=10, height=10)

    result = CreateSemanticSegmentation.from_rle_mask(
        label="cat",
        segmentation_mask=rle_mask,
        two_dim_sample=image_sample,
        confidence=0.9,
    )

    assert result.label == "cat"
    assert result.confidence == pytest.approx(0.9)
    assert result.x == 3
    assert result.y == 2
    assert result.width == 2
    assert result.height == 2
    assert result.segmentation_mask == rle_mask
