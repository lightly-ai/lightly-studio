"""Helpers for deterministic annotation layer ordering."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable


def sort_annotations_by_layer(
    annotations: Sequence[AnnotationBaseTable],
) -> list[AnnotationBaseTable]:
    """Sort annotations by layer stack position from top to bottom."""
    return sorted(
        annotations,
        key=lambda annotation: (
            annotation.layer.position if annotation.layer is not None else -1,
            annotation.created_at,
            str(annotation.sample_id),
        ),
        reverse=True,
    )
