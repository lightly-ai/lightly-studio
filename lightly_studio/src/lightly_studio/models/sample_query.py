"""Request and response models of the sample query that the Python client uses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Self
from uuid import UUID

import pydantic
from pydantic import BaseModel

from lightly_studio.models.query_expr import FieldRef, QueryExpr
from lightly_studio.models.sort_direction import SortDirection

DEFAULT_PAGE_SIZE = 256
MAX_PAGE_SIZE = 1000


class SampleInclude(str, Enum):
    """Related data that the sample query returns with each sample."""

    TAGS = "tags"
    METADATA = "metadata"
    CAPTIONS = "captions"
    ANNOTATIONS = "annotations"


class SortKey(BaseModel):
    """One key of the sort order, on a field.

    Attributes:
        field: The field to sort by.
        direction: The sort direction.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    field: FieldRef
    direction: SortDirection = SortDirection.asc


class EvaluationMetricSortKey(BaseModel):
    """One key of the sort order, on a sample metric of an evaluation run.

    Attributes:
        run_name: The name of the evaluation run.
        metric_name: The name of the metric to sort by.
        direction: The sort direction.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    run_name: str
    metric_name: str
    direction: SortDirection = SortDirection.asc


class SampleQueryRequest(BaseModel):
    """Filter, sort and page of a sample query.

    Attributes:
        query_expr: The filter. None matches all samples of the collection.
        sort: The sort keys. Empty sorts by creation time. The sample ID always breaks ties.
        cursor: The `next_cursor` of the previous page. None gets the first page.
        limit: The maximum number of samples in the page.
        offset: The number of samples to skip on the first page.
        include: The related data to return with each sample.
    """

    query_expr: QueryExpr | None = None
    sort: list[SortKey | EvaluationMetricSortKey] = []
    cursor: str | None = None
    limit: int = pydantic.Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    offset: int = pydantic.Field(default=0, ge=0)
    include: list[SampleInclude] = []

    @pydantic.model_validator(mode="after")
    def validate_offset(self) -> Self:  # noqa: N804
        """Reject an offset together with a cursor."""
        if self.cursor is not None and self.offset > 0:
            raise ValueError("Use offset only on the first page, without a cursor.")
        return self


class ImageSampleRecord(BaseModel):
    """The fields of an image sample, without a database session.

    Attributes:
        sample_id: The ID of the sample.
        collection_id: The ID of the collection of the sample.
        created_at: The creation time of the sample.
        updated_at: The time of the last change of the sample.
        file_name: The file name of the image.
        file_path_abs: The absolute path of the image file.
        width: The image width in pixels.
        height: The image height in pixels.
        tags: The sorted tag names. None if the query did not include tags.
    """

    sample_id: UUID
    collection_id: UUID
    created_at: datetime
    updated_at: datetime
    file_name: str
    file_path_abs: str
    width: int
    height: int
    tags: list[str] | None = None


class SamplePage(BaseModel):
    """One page of a sample query.

    Attributes:
        samples: The samples of the page.
        next_cursor: The cursor of the next page. None on the last page.
    """

    samples: list[ImageSampleRecord]
    next_cursor: str | None = None
