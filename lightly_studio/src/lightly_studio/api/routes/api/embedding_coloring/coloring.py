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
    """Return (color_categories, color_legend).

    Only MetadataFieldColorBy is handled. For other ColorBy variants or None,
    color_categories equals fulfils_filter and the legend is empty.
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
