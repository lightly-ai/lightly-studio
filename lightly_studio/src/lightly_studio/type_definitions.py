"""Common type definitions for the lightly_studio package."""

from pathlib import Path
from typing import TypeVar, Union
from uuid import UUID

from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable

# Generic query type for filters that work with both data queries and count queries
QueryType = TypeVar(
    "QueryType",
    SelectOfScalar[AnnotationBaseTable],
    SelectOfScalar[ImageTable],
    SelectOfScalar[int],
    SelectOfScalar[UUID],
    SelectOfScalar[SampleTable],
    SelectOfScalar[SampleEmbeddingTable],
)

PathLike = Union[str, Path]
