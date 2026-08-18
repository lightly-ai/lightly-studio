"""Build a SQL count expression for annotation count mode."""

from __future__ import annotations

from sqlalchemy import ColumnElement
from sqlmodel import col, func

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def build_count_expression(count_mode: AnnotationCountMode) -> ColumnElement[int]:
    """Return a SQL count expression for the given count mode."""
    if count_mode == AnnotationCountMode.SAMPLES:
        return func.count(func.distinct(col(AnnotationBaseTable.parent_sample_id)))
    return func.count(col(AnnotationBaseTable.sample_id))
