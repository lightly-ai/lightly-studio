"""Tests for the sRGB to linear RGB conversion."""

import numpy as np
import pytest

from lightly_studio.services.recording_service import srgb_to_linear


def test_srgb_to_linear() -> None:
    channel = np.array([0, 255], dtype=np.uint8)

    result = srgb_to_linear.srgb_to_linear(channel=channel)

    assert result.dtype == np.float32
    assert result == pytest.approx([0.0, 1.0])


def test_srgb_to_linear__below_threshold_divides_by_12_92() -> None:
    channel = np.array([10], dtype=np.uint8)

    result = srgb_to_linear.srgb_to_linear(channel=channel)

    # 10 / 255 is below the linear threshold, so the channel divides by 12.92.
    assert result == pytest.approx([(10 / 255) / 12.92])
