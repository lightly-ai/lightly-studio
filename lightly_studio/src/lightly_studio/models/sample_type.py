"""Defines the SampleType enum used to specify the type of samples in a dataset."""

from enum import Enum

class SampleType(str, Enum):
    """The type of samples in the dataset."""

    VIDEO = "video"
    IMAGE = "image"
    IMAGE_ANNOTATION = "image_annotation"
