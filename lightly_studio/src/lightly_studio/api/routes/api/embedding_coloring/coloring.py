"""Coloring logic for 2D embedding plots."""

from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session
from typing_extensions import assert_never

from lightly_studio.api.routes.api.embedding_coloring import (
    annotations as annotation_coloring,
)
from lightly_studio.api.routes.api.embedding_coloring import (
    metadata,
    tags,
)
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import ColorData


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
    matching_sample_ids: set[UUID] | None,
) -> ColorData:
    """Build color categories and a legend for embedding coloring.

    Args:
        session: Database session used to resolve metadata values.
        collection_id: Collection whose samples are being colored.
        color_by: Coloring configuration to apply to the samples.
        sample_ids: Sample IDs in the same order as the returned color categories.
        matching_sample_ids: Sample IDs matching the active filter. Values are
            prioritized by their frequency among these samples so the legend
            reflects the filtered view. ``None`` means no filter is active (all
            samples are counted).

    Returns:
        The `ColorData` for the provided samples: one color-category list per
        sample (sorted ascending), a legend mapping color ID to a human-readable
        string, and an `ordered` flag set for ordered (numeric) color scales.
    """
    if isinstance(color_by, TagColorBy):
        color_categories, color_legend = tags.build_tag_color_maps(
            session=session,
            tag_ids=color_by.tag_ids,
            sample_ids=sample_ids,
            matching_sample_ids=matching_sample_ids,
        )
        return ColorData(color_categories=color_categories, color_legend=color_legend)

    if isinstance(color_by, MetadataFieldColorBy):
        return metadata.build_metadata_color_maps(
            session=session,
            collection_id=collection_id,
            key=color_by.key,
            sample_ids=sample_ids,
            matching_sample_ids=matching_sample_ids,
        )

    if isinstance(color_by, AnnotationColorBy):
        color_categories, color_legend = annotation_coloring.build_annotation_color_maps(
            session=session,
            annotation_label_ids=color_by.annotation_label_ids,
            sample_ids=sample_ids,
            matching_sample_ids=matching_sample_ids,
        )
        return ColorData(color_categories=color_categories, color_legend=color_legend)

    # Static check that all ColorBy variants are handled above.
    if color_by is not None:
        assert_never(color_by)

    return ColorData(color_categories=[[] for _ in sample_ids], color_legend={})
