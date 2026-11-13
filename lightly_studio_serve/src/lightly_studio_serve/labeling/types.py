"""Value types that labeling models return.

Holds ``PredictedAnnotation``. It lives in its own module so any caller can depend on
it without importing the ``LabelingModel`` class.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PredictedAnnotation:
    """An annotation that a labeling model predicted, before the user saves it.

    <span class="doc-badge doc-badge--beta">Beta</span>

    H is the image height and W is the image width, in pixels. Two predicted
    annotations are equal when all fields are equal, including the mask values.
    """

    class_name: str
    """Name of the predicted annotation class."""

    box: tuple[float, float, float, float]
    """Bounding box ``(x_min, y_min, x_max, y_max)`` in pixels, as floats.

    LightlyStudio converts it to the smallest integer box that contains it.
    """

    score: float
    """Confidence score, from 0 to 1."""

    mask: NDArray[np.bool_] | None = None
    """Mask of shape ``(H, W)`` and dtype ``np.bool_``, or None for a model without masks."""

    def __eq__(self, other: object) -> bool:
        """Compare all fields. Compare the masks by value, not by identity."""
        if not isinstance(other, PredictedAnnotation):
            return NotImplemented
        if (self.class_name, self.box, self.score) != (other.class_name, other.box, other.score):
            return False
        if self.mask is None or other.mask is None:
            return self.mask is None and other.mask is None
        return np.array_equal(self.mask, other.mask)

    def __hash__(self) -> int:
        """Hash all fields except the mask, because a NumPy array has no hash."""
        return hash((self.class_name, self.box, self.score))
