"""Provider interface for assisted labeling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import numpy as np
from numpy.typing import NDArray


class ProviderError(Exception):
    """Raised when a provider cannot compute a segmentation.

    API callers see the message, so it must not hold provider output.
    """


class ProviderUnavailableError(Exception):
    """Raised when the provider is not configured, for example without an API key."""


@dataclass(frozen=True)
class ProviderImage:
    """An image that a provider segments.

    Attributes:
        sample_id: ID of the image sample. Providers use it as a cache key.
        width: Image width in pixels.
        height: Image height in pixels.
        file_name: File name of the image, for example `img.jpg`.
        read_bytes: Returns the encoded image file content. Providers call it only when
            they need the image data.
    """

    sample_id: UUID
    width: int
    height: int
    file_name: str
    read_bytes: Callable[[], bytes]


@dataclass(frozen=True)
class PointPrompt:
    """A point prompt in integer pixel coordinates.

    Attributes:
        x: Column of the pixel, from 0 to image width - 1.
        y: Row of the pixel, from 0 to image height - 1.
        positive: True if the pixel is on the object, False if it is on the background.
    """

    x: int
    y: int
    positive: bool


@dataclass(frozen=True)
class BoxPrompt:
    """A box prompt in integer pixel coordinates.

    The minimum coordinates are inclusive and the maximum coordinates are exclusive.

    Attributes:
        x_min: Left edge, from 0 to image width - 1.
        y_min: Top edge, from 0 to image height - 1.
        x_max: Right edge, from x_min + 1 to image width.
        y_max: Bottom edge, from y_min + 1 to image height.
    """

    x_min: int
    y_min: int
    x_max: int
    y_max: int


@dataclass
class SegmentationPrompt:
    """All prompts of one segmentation request.

    Attributes:
        points: Positive and negative point prompts.
        boxes: Box prompts.
        text: Text prompt, for example a class name.
        max_masks: Maximum number of masks to return. 1 selects the interactive
            single-object mode.
    """

    points: list[PointPrompt]
    boxes: list[BoxPrompt]
    text: str | None
    max_masks: int


@dataclass
class Prediction:
    """A predicted segmentation mask.

    H is image height and W is image width in pixels.

    Attributes:
        mask: Full-image mask of shape (H, W) and dtype `np.bool_`.
        score: Confidence score, if the provider returns one.
    """

    mask: NDArray[np.bool_]
    score: float | None


class AssistedLabelingProvider(Protocol):
    """A model backend that computes segmentation masks from prompts."""

    def unavailable_reason(self) -> str | None:
        """Returns None if the provider is usable, else a human-readable reason."""
        ...

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:
        """Computes segmentation masks for the image and the prompt.

        Args:
            image: Image to segment.
            prompt: Prompts to guide segmentation.

        Returns:
            Predicted segmentation masks.

        Raises:
            ProviderUnavailableError: If the provider is not configured.
            ProviderError: If the segmentation fails.
        """
        ...
