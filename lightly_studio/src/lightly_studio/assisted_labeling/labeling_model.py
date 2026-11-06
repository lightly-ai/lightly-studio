"""Interface of the models that label images in the GUI."""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from PIL import Image


class ModelTask(str, Enum):
    """The task of a labeling model."""

    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"


@dataclass(frozen=True)
class LabelingImage:
    """An image that a model labels.

    Attributes:
        sample_id: ID of the image sample. Use it as a cache key.
        width: Image width in pixels.
        height: Image height in pixels.
        file_name: File name of the image, for example `img.jpg`.
        read_bytes: Returns the encoded image file content. Call it only when you need
            the image data.
    """

    sample_id: UUID
    width: int
    height: int
    file_name: str
    read_bytes: Callable[[], bytes]

    def to_pil(self) -> Image.Image:
        """Returns the decoded image."""
        image = Image.open(io.BytesIO(self.read_bytes()))
        image.load()
        return image


@dataclass
class PredictedAnnotation:
    """An annotation that a model predicted, before the user saves it.

    H is image height and W is image width in pixels.

    Attributes:
        class_name: Name of the predicted annotation class.
        box: Bounding box `(x_min, y_min, x_max, y_max)` in pixels. LightlyStudio clamps
            it to the image.
        score: Confidence score, from 0 to 1.
        mask: Full-image mask of shape (H, W) and dtype `np.bool_`, or None if the model
            predicts no masks.
    """

    class_name: str
    box: tuple[float, float, float, float]
    score: float
    mask: NDArray[np.bool_] | None = None


class LabelingModel(ABC):
    """A model that labels images in the GUI.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Subclass it to use your own model for labeling, then register an instance with
    `register_labeling_model` before you start the GUI. The GUI shows the "Label with
    model" tool when at least one model is registered. `task` tells the GUI which
    annotations the model predicts.

    The GUI server calls `predict` from several threads, so it must be thread-safe.
    """

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Unique ID of the model, for example `ltdetrv2-s-coco`. The GUI shows it."""

    @property
    @abstractmethod
    def task(self) -> ModelTask:
        """Task of the model."""

    @property
    @abstractmethod
    def class_names(self) -> list[str]:
        """Names of the annotation classes that the model can predict."""

    @property
    def vendor(self) -> str:
        """Who runs the model. Used for usage reports."""
        return "local"

    @abstractmethod
    def predict(self, image: LabelingImage, threshold: float) -> list[PredictedAnnotation]:
        """Predicts the annotations of the image.

        LightlyStudio drops the predicted annotations with a score below `threshold`
        after this call, so the model can ignore `threshold` or use it to skip work.

        Args:
            image: Image to label.
            threshold: Minimum confidence score that the user selected, from 0 to 1.

        Returns:
            Predicted annotations in any order.

        Raises:
            ProviderError: If the model fails. The GUI shows the message.
        """
