"""Runs labeling models on the images of a dataset.

A runner hides where a model runs. The services call a runner with a ``ProviderImage``
and never call a ``LabelingModel`` directly.
"""

from __future__ import annotations

import io
import logging
from typing import Protocol

from lightly_studio_serve.labeling_model import LabelingModel, ModelTask
from lightly_studio_serve.types import PredictedAnnotation
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from PIL.Image import Image

from lightly_studio.assisted_labeling.provider import (
    ProviderError,
    ProviderImage,
    ProviderNotCalledError,
)

logger = logging.getLogger(__name__)


class LabelingModelRunner(Protocol):
    """A labeling model that LightlyStudio can run on an image of a dataset."""

    @property
    def model_id(self) -> str:
        """Unique ID of the model."""

    @property
    def task(self) -> ModelTask:
        """The kind of annotations that the model predicts."""

    @property
    def class_names(self) -> list[str]:
        """Names of the annotation classes that the model can predict."""

    def predict(self, image: ProviderImage, threshold: float) -> list[PredictedAnnotation]:
        """Predict the annotations of the image.

        Args:
            image: The image to label.
            threshold: The minimum confidence score that the user selected, from 0 to 1.

        Returns:
            The predicted annotations, as the model returned them.

        Raises:
            NotFoundError: If the image file cannot be read.
            ProviderNotCalledError: If the run fails before it reaches the model.
            ProviderError: If the model fails.
        """


class LocalLabelingModelRunner:
    """Runs a labeling model that is registered in this process."""

    def __init__(self, model: LabelingModel) -> None:
        """Create a runner for the model."""
        self._model = model

    @property
    def model_id(self) -> str:
        """Unique ID of the model."""
        return self._model.model_id

    @property
    def task(self) -> ModelTask:
        """The kind of annotations that the model predicts."""
        return self._model.task

    @property
    def class_names(self) -> list[str]:
        """Names of the annotation classes that the model can predict."""
        return self._model.class_names

    def predict(self, image: ProviderImage, threshold: float) -> list[PredictedAnnotation]:
        """Decode the image file and predict its annotations with the model.

        The model gets an RGB image.

        Raises:
            NotFoundError: If the image file cannot be read.
            ProviderNotCalledError: If the image file cannot be decoded.
            ProviderError: If the model raises an error.
        """
        pil_image = _decode(image=image)
        try:
            return self._model.predict(image=pil_image, threshold=threshold)
        except Exception as error:
            # The message names the class alone. The text of an error can hold model output.
            logger.exception("Labeling model %r failed.", self.model_id)
            raise ProviderError(
                f"The labeling model {self.model_id!r} raised {type(error).__name__}. "
                "See the server log."
            ) from error


def _decode(image: ProviderImage) -> Image:
    """Decode the image file to an RGB image.

    Raises:
        NotFoundError: If the image file cannot be read.
        ProviderNotCalledError: If the image file cannot be decoded.
    """
    data = image.read_bytes()
    try:
        with PILImage.open(io.BytesIO(data)) as image_file:
            return image_file.convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ProviderNotCalledError(
            f"The image file {image.file_name!r} cannot be decoded."
        ) from error
