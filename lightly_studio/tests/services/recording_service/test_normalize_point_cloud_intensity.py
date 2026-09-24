"""Tests for point-cloud intensity normalization."""

import numpy as np

from lightly_studio.services.recording_service import normalize_point_cloud_intensity


def test_normalize_point_cloud_intensity() -> None:
    values = np.array([2.0, 4.0, np.nan], dtype=np.float32)

    result = normalize_point_cloud_intensity.normalize_point_cloud_intensity(values=values)

    np.testing.assert_array_equal(result, np.array([0.0, 1.0, 0.0], dtype=np.float32))


def test_normalize_point_cloud_intensity__constant_values() -> None:
    values = np.array([3.0, 3.0], dtype=np.float32)

    result = normalize_point_cloud_intensity.normalize_point_cloud_intensity(values=values)

    np.testing.assert_array_equal(result, np.zeros(2, dtype=np.float32))


def test_normalize_point_cloud_intensity__preserves_precision() -> None:
    values = np.array([16777216, 16777217], dtype=np.uint32)

    result = normalize_point_cloud_intensity.normalize_point_cloud_intensity(values=values)

    np.testing.assert_array_equal(result, np.array([0.0, 1.0], dtype=np.float32))


def test_normalize_point_cloud_intensity__all_nonfinite() -> None:
    values = np.array([np.nan, np.inf, -np.inf], dtype=np.float32)

    result = normalize_point_cloud_intensity.normalize_point_cloud_intensity(values=values)

    np.testing.assert_array_equal(result, np.zeros(3, dtype=np.float32))
