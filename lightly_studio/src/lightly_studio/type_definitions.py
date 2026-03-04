"""Common type definitions for the lightly_studio package."""

from pathlib import Path
from typing import Any, TypeVar, Union
from uuid import UUID

from sqlmodel.sql.expression import Select, SelectOfScalar

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.group import GroupTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.video import VideoFrameTable, VideoTable

# Generic query type for filters that work with both data queries and count queries
QueryType = TypeVar(
    "QueryType",
    SelectOfScalar[AnnotationBaseTable],
    SelectOfScalar[ImageTable],
    SelectOfScalar[int],
    SelectOfScalar[UUID],
    SelectOfScalar[SampleTable],
    SelectOfScalar[SampleEmbeddingTable],
    SelectOfScalar[GroupTable],
    Select[tuple[VideoTable, VideoFrameTable]],
    SelectOfScalar[VideoFrameTable],
    Select[tuple[Any, int]],
    Select[tuple[UUID, int]],
    Select[tuple[AnnotationBaseTable, Any]],
    Select[tuple[ImageTable, float]],
    Select[tuple[GroupTable, float]],
    Select[tuple[VideoTable, VideoFrameTable, float]],
)

PathLike = Union[str, Path]
