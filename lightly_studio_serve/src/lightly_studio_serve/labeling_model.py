"""Interface of the models that label images in the LightlyStudio GUI.

Defines the ``LabelingModel`` base class and the ``ModelTask`` that a model declares.
A concrete model implements ``predict`` and names its ID, its task and its annotation
classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from PIL.Image import Image

from lightly_studio_serve.types import PredictedAnnotation


class ModelTask(str, Enum):
    """The kind of annotations that a labeling model predicts.

    <span class="doc-badge doc-badge--beta">Beta</span>
    """

    OBJECT_DETECTION = "object_detection"
    """The model predicts bounding boxes."""

    INSTANCE_SEGMENTATION = "instance_segmentation"
    """The model predicts one mask for each object."""


class LabelingModel(ABC):
    """Base class for a model that labels images in the GUI.

    <span class="doc-badge doc-badge--beta">Beta</span>

    Subclass it to label images with your own model. The GUI runs the model on the open
    image and shows the predicted annotations. The user deletes the wrong ones and saves
    the rest.

    A labeling model must accept calls from more than one thread, because the server runs
    a request in a worker thread. Hold a lock in ``predict`` when the model cannot.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Unique ID of the model, for example ``ltdetrv2-s-coco``. The GUI shows it."""

    @property
    @abstractmethod
    def task(self) -> ModelTask:
        """The kind of annotations that the model predicts."""

    @property
    @abstractmethod
    def class_names(self) -> list[str]:
        """Names of the annotation classes that the model can predict."""

    @property
    def ready(self) -> bool:
        """Whether the model is loaded and can answer requests.

        The default suits a model that loads when the object exists. Override the
        property when the weights load in the background. ``model_id``, ``task`` and
        ``class_names`` must answer either way.
        """
        return True

    @abstractmethod
    def predict(self, image: Image, threshold: float) -> list[PredictedAnnotation]:
        """Predict the annotations of one image.

        LightlyStudio drops the predicted annotations with a score below ``threshold``
        after this call. The model can ignore ``threshold``, or use it to skip work.

        Args:
            image: The image to label.
            threshold: The minimum confidence score that the user selected, from 0 to 1.

        Returns:
            The predicted annotations, in any order. Every ``class_name`` must be one
            of ``class_names``.
        """
