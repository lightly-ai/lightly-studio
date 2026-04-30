"""Models for dataset sorting fields."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SortAggregateFn(str, Enum):
    """Aggregate functions supported for repeated sort fields."""

    MIN = "min"
    MAX = "max"
    AVG = "avg"
    COUNT = "count"


class SortFieldSource(str, Enum):
    """Sources supported for sort fields."""

    IMAGE = "image"
    SAMPLE = "sample"
    OBJECT_DETECTION = "object_detection"
    METADATA = "metadata"
    TAGS = "tags"


class SortDirection(str, Enum):
    """Directions supported for sort fields."""

    ASC = "asc"
    DESC = "desc"


class SortFieldSpec(BaseModel):
    """Field that can be selected for sorting in the GUI."""

    id: str
    field_name: str
    label: str
    source: SortFieldSource
    aggregate_fn: SortAggregateFn | None = None


class SortFieldExpr(BaseModel):
    """Sort field selected by the GUI."""

    id: str
    field_name: str
    source: SortFieldSource
    aggregate_fn: SortAggregateFn | None = None
    direction: SortDirection
