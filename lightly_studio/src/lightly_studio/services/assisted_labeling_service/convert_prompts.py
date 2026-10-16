"""Conversion of normalized prompts to integer pixel prompts."""

from __future__ import annotations

import math

from lightly_studio.assisted_labeling.provider import BoxPrompt, PointPrompt
from lightly_studio.models.assisted_labeling import AnnotationBox, AnnotationPoint


def to_point_prompt(point: AnnotationPoint, width: int, height: int) -> PointPrompt:
    """Returns the pixel that contains the normalized point."""
    return PointPrompt(
        x=_clamp(value=math.floor(point.x * width), upper=width - 1),
        y=_clamp(value=math.floor(point.y * height), upper=height - 1),
        positive=point.positive,
    )


def to_box_prompt(box: AnnotationBox, width: int, height: int) -> BoxPrompt:
    """Returns the smallest pixel box that contains the normalized box."""
    x_min = _clamp(value=math.floor(box.x * width), upper=width - 1)
    y_min = _clamp(value=math.floor(box.y * height), upper=height - 1)
    x_max = _clamp(value=math.ceil((box.x + box.width) * width), upper=width)
    y_max = _clamp(value=math.ceil((box.y + box.height) * height), upper=height)
    return BoxPrompt(
        x_min=x_min,
        y_min=y_min,
        x_max=max(x_max, x_min + 1),
        y_max=max(y_max, y_min + 1),
    )


def _clamp(value: int, upper: int) -> int:
    return max(0, min(value, upper))
