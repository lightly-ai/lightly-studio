"""This module defines the SampleViewType enum."""

from enum import Enum


class SampleViewType(str, Enum):
    """Enum for sample view types."""

    IMAGE = "image"
    VIDEO = "video"
