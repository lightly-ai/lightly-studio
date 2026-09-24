"""Normalize sensor intensity values for point-cloud rendering."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def normalize_point_cloud_intensity(values: NDArray[Any]) -> NDArray[Any]:
    """Scale finite sensor intensity values into the renderer's [0, 1] range."""
    values = values.astype(np.float32)
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values)
    minimum = float(values[finite].min())
    maximum = float(values[finite].max())
    if maximum <= minimum:
        return np.zeros_like(values)
    normalized = np.clip((values - minimum) / (maximum - minimum), 0.0, 1.0)
    normalized[~finite] = 0.0
    return normalized
