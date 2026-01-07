"""Common type definitions for the lightly_studio package."""

from pathlib import Path
from typing import Any, Tuple, TypeVar, Union
from uuid import UUID

from sqlmodel.sql.expression import Select, SelectOfScalar

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
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
    Select[Tuple[VideoTable, VideoFrameTable]],
    SelectOfScalar[VideoFrameTable],
    Select[Tuple[Any, int]],
    Select[Tuple[UUID, int]],
    Select[Tuple[AnnotationBaseTable, Any]],
    Select[Tuple[ImageTable, float]],
    Select[Tuple[VideoTable, VideoFrameTable, float]],
)

PathLike = Union[str, Path]
