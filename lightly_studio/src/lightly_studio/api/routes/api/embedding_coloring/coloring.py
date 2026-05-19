"""Coloring logic for 2D embedding plots."""

from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import metadata

# Categories 0 and 1 are reserved (0 = excluded by filter, 1 = unassigned),
# so real color categories start at 2.
_COLOR_OFFSET = 2


class TagColorBy(BaseModel):
    """Color samples by tag membership."""

    type: Literal["tag"] = "tag"
    tag_ids: list[UUID]


class MetadataFieldColorBy(BaseModel):
    """Assign a distinct color to each unique value of the selected field."""

    type: Literal["metadata_field"] = "metadata_field"
    key: str


class AnnotationColorBy(BaseModel):
    """Color samples by annotation label."""

    type: Literal["annotation"] = "annotation"
    annotation_label_ids: list[UUID]


ColorBy = Annotated[
    Union[TagColorBy, MetadataFieldColorBy, AnnotationColorBy],
    Field(discriminator="type"),
]


def build_color_data(
    session: Session,
    collection_id: UUID,
    color_by: ColorBy | None,
    sample_ids: list[UUID],
    fulfils_filter: list[int],
) -> tuple[list[int], dict[int, str]]:
    """Build color categories and a legend for embedding coloring.

    Args:
        session: Database session used to resolve metadata values.
        collection_id: Collection whose samples are being colored.
        color_by: Coloring configuration to apply to the samples.
        sample_ids: Sample IDs in the same order as the returned color categories.
        fulfils_filter: Per-sample filter categories used as the fallback coloring.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples. The
        length of `color_categories` is the number of samples. The `color_legend` is a mapping
        from color ID to a human-readable string.
    """
    if not isinstance(color_by, MetadataFieldColorBy):
        return list(fulfils_filter), {}

    color_categories, legend = metadata.build_metadata_color_maps(
        session=session,
        collection_id=collection_id,
        key=color_by.key,
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        start_cat=_COLOR_OFFSET,
    )
    legend[1] = "Unassigned"
    return color_categories, legend
