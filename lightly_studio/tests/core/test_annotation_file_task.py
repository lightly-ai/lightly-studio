"""Tests for the annotation file task."""

from __future__ import annotations

import pytest

from lightly_studio.core import annotation_file_task
from lightly_studio.core.annotation_file_task import AnnotationFileTask
from lightly_studio.models.annotation.annotation_base import AnnotationType


def test_resolve_annotation_task__both_set() -> None:
    with pytest.raises(ValueError, match="Pass either annotation_task or annotation_type"):
        annotation_file_task.resolve_annotation_task(
            annotation_task=AnnotationFileTask.OBJECT_DETECTION,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )


@pytest.mark.parametrize(
    ("annotation_type", "expected"),
    [
        (AnnotationType.OBJECT_DETECTION, AnnotationFileTask.OBJECT_DETECTION),
        (AnnotationType.SEGMENTATION_MASK, AnnotationFileTask.INSTANCE_SEGMENTATION),
    ],
)
def test_resolve_annotation_task__annotation_type_deprecated(
    annotation_type: AnnotationType, expected: AnnotationFileTask
) -> None:
    with pytest.warns(DeprecationWarning, match="annotation_type is deprecated"):
        result = annotation_file_task.resolve_annotation_task(
            annotation_task=None, annotation_type=annotation_type
        )

    assert result == expected


def test_resolve_annotation_task__invalid_annotation_type() -> None:
    with (
        pytest.warns(DeprecationWarning, match="deprecated"),
        pytest.raises(ValueError, match="Invalid annotation"),
    ):
        annotation_file_task.resolve_annotation_task(
            annotation_task=None, annotation_type=AnnotationType.CLASSIFICATION
        )


def test_resolve_annotation_task__task_only() -> None:
    result = annotation_file_task.resolve_annotation_task(
        annotation_task=AnnotationFileTask.INSTANCE_SEGMENTATION, annotation_type=None
    )

    assert result == AnnotationFileTask.INSTANCE_SEGMENTATION


def test_resolve_annotation_task__default() -> None:
    result = annotation_file_task.resolve_annotation_task(
        annotation_task=None, annotation_type=None
    )

    assert result == AnnotationFileTask.OBJECT_DETECTION
