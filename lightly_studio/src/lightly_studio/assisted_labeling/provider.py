"""Provider interface for AI-assisted segmentation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel


class ProviderError(Exception):
    """Raised when a provider cannot compute a segmentation."""


class ProviderUnavailableError(Exception):
    """Raised when the active provider is not usable, for example without an API key."""


class ProviderCapabilities(BaseModel):
    """Prompt types and limits that a provider supports."""

    positive_points: bool
    negative_points: bool
    boxes: bool
    text_prompt: bool
    max_instances: int


class OutputType(str, Enum):
    """Geometry that a segmentation request asks for."""

    MASK = "mask"
    BOX = "box"


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
    """A point prompt in integer pixel coordinates."""

    x: int
    y: int
    positive: bool


@dataclass(frozen=True)
class BoxPrompt:
    """A box prompt in integer pixel coordinates."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int


@dataclass(frozen=True)
class SegmentationPrompt:
    """All prompts of one segmentation request.

    Attributes:
        points: Positive and negative point prompts.
        boxes: Box prompts.
        text: Text prompt, for example a class name.
        max_masks: Maximum number of masks to return. 1 selects the interactive
            single-object mode.
        output_type: Requested geometry. With `OutputType.BOX`, a provider can return
            filled box masks. Providers that always compute exact masks ignore it.
    """

    points: list[PointPrompt]
    boxes: list[BoxPrompt]
    text: str | None
    max_masks: int
    output_type: OutputType = OutputType.MASK


@dataclass
class Prediction:
    """A predicted segmentation mask.

    Attributes:
        mask: Full-image mask of shape (H, W) and dtype `np.bool_`.
        score: Confidence score, if the provider returns one.
        class_name: Class name, if the provider returns one.
    """

    mask: NDArray[np.bool_]
    score: float | None
    class_name: str | None


class AssistedLabelingProvider(Protocol):
    """A model backend that computes segmentation masks from prompts."""

    @property
    def provider_id(self) -> str:
        """Stable ID of the provider, for example `fal_sam3`."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name of the provider."""
        ...

    @property
    def sends_data_to_third_party(self) -> bool:
        """True if the provider sends image data to a third party."""
        ...

    def capabilities(self) -> ProviderCapabilities:
        """Returns the prompt types and limits that the provider supports."""
        ...

    def is_available(self) -> str | None:
        """Returns None if the provider is usable, else a human-readable reason."""
        ...

    def prepare(self, image: ProviderImage) -> None:
        """Prepares an image for later segment calls, for example by uploading it.

        Raises:
            ProviderError: If the preparation fails.
        """
        ...

    def segment(self, image: ProviderImage, prompt: SegmentationPrompt) -> list[Prediction]:
        """Computes segmentation masks for the image and the prompt.

        Raises:
            ProviderError: If the segmentation fails.
        """
        ...
