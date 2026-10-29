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
    """Color samples by the value of a metadata field.

    String and boolean values get a distinct color each, numeric values a gradient.
    """

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
        The color data for the provided samples. The length of `color_categories`
        is the number of samples; each entry is the list of that sample's color
        categories, sorted ascending. The `color_legend` is a mapping from color ID
        to a human-readable string. Numeric metadata fields also get a `color_gradient`.
    """
    if isinstance(color_by, TagColorBy):
        categories, legend = tags.build_tag_color_maps(
            session=session,
            tag_ids=color_by.tag_ids,
            sample_ids=sample_ids,
            matching_sample_ids=matching_sample_ids,
        )
        return ColorData(color_categories=categories, color_legend=legend)

    if isinstance(color_by, MetadataFieldColorBy):
        return metadata.build_metadata_color_maps(
            session=session,
            collection_id=collection_id,
            key=color_by.key,
            sample_ids=sample_ids,
            matching_sample_ids=matching_sample_ids,
        )

    if isinstance(color_by, AnnotationColorBy):
        categories, legend = annotation_coloring.build_annotation_color_maps(
            session=session,
            annotation_label_ids=color_by.annotation_label_ids,
            sample_ids=sample_ids,
            matching_sample_ids=matching_sample_ids,
        )
        return ColorData(color_categories=categories, color_legend=legend)

    # Static check that all ColorBy variants are handled above.
    if color_by is not None:
        assert_never(color_by)

    return ColorData(color_categories=[[] for _ in sample_ids], color_legend={})
