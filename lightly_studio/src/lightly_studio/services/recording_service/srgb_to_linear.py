"""Convert an sRGB color channel to linear RGB."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from lightly_studio.services.recording_service.point_cloud_types import SRGB_LINEAR_THRESHOLD


def srgb_to_linear(channel: NDArray[Any]) -> NDArray[np.float32]:
    """Convert an sRGB 0-255 color channel to linear RGB per the renderer contract.

    Args:
        channel: The sRGB channel values in the 0-255 range.

    Returns:
        The linear RGB channel values in the 0-1 range.
    """
    srgb = channel.astype(np.float32) / 255.0
    linear = np.where(srgb <= SRGB_LINEAR_THRESHOLD, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return linear.astype(np.float32)
