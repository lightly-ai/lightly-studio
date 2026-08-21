"""Build a SQL count expression for annotation count mode."""

from __future__ import annotations

import sqlmodel
from sqlalchemy import ColumnElement

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def build_count_expression(count_mode: AnnotationCountMode) -> ColumnElement[int]:
    """Return a SQL count expression for the given count mode."""
    if count_mode == AnnotationCountMode.SAMPLES:
        distinct = sqlmodel.func.distinct(sqlmodel.col(AnnotationBaseTable.parent_sample_id))
        return sqlmodel.func.count(distinct)
    return sqlmodel.func.count(sqlmodel.col(AnnotationBaseTable.sample_id))
