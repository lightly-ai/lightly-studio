"""Interface of the models that label images in the LightlyStudio GUI."""

from lightly_studio_serve.labeling.labeling import LabelingModel, ModelTask
from lightly_studio_serve.labeling.types import PredictedAnnotation

__all__ = ["LabelingModel", "ModelTask", "PredictedAnnotation"]
