"""Annotation file task and resolution of the deprecated annotation type argument."""

from __future__ import annotations

import warnings
from enum import Enum

from lightly_studio.models.annotation.annotation_base import AnnotationType


class AnnotationFileTask(str, Enum):
    """The task that an annotation file describes."""

    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"


def resolve_annotation_task(
    annotation_task: AnnotationFileTask | None,
    annotation_type: AnnotationType | None,
) -> AnnotationFileTask:
    """Resolve the annotation task from the new and the deprecated argument.

    Args:
        annotation_task: The annotation task.
        annotation_type: Deprecated. Use `annotation_task` instead.

    Returns:
        The annotation task. Defaults to object detection if both arguments are `None`.

    Raises:
        ValueError: If both arguments are set or the annotation type is not supported.
    """
    if annotation_task is not None and annotation_type is not None:
        raise ValueError("Pass either annotation_task or annotation_type, not both.")
    if annotation_type is not None:
        warnings.warn(
            "annotation_type is deprecated, use annotation_task instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        if annotation_type == AnnotationType.OBJECT_DETECTION:
            return AnnotationFileTask.OBJECT_DETECTION
        if annotation_type == AnnotationType.SEGMENTATION_MASK:
            return AnnotationFileTask.INSTANCE_SEGMENTATION
        raise ValueError(f"Invalid annotation type: {annotation_type}")
    if annotation_task is not None:
        return annotation_task
    return AnnotationFileTask.OBJECT_DETECTION
