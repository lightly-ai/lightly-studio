"""Metadata-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import coloring_helpers
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.resolvers.metadata_resolver import sample as sample_metadata_resolver


def build_metadata_color_maps(
    session: Session,
    collection_id: UUID,
    key: str,
    sample_ids: list[UUID],
) -> tuple[list[list[int]], dict[int, str]]:
    """Build color categories and a legend for metadata-based sample coloring.

    A metadata key holds a single value per sample, so each sample maps to a
    single-element category list. The list shape keeps this consistent with the
    other coloring sources (tags, annotations).

    Args:
        session: Database session.
        collection_id: ID of the collection whose metadata should be used.
        key: Metadata field used for coloring.
        sample_ids: Sample IDs in the order for which to build color categories.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples. The
        length of `color_categories` is the number of samples; each entry is a
        single-element list. The `color_legend` is a mapping from color ID to a
        human-readable string.
    """
    sample_to_value, metadata_type = sample_metadata_resolver.get_metadata_values_for_key(
        session=session,
        collection_id=collection_id,
        key=key,
    )
    scale = _build_metadata_color_scale(
        key=key,
        sample_to_value=sample_to_value,
        metadata_type=metadata_type,
    )
    return coloring_helpers.assign_color_category_lists(
        sample_ids=sample_ids,
        sample_to_values={sid: (value,) for sid, value in sample_to_value.items()},
        scale=scale,
    )


def _build_metadata_color_scale(
    key: str,
    sample_to_value: dict[UUID, Any],
    metadata_type: str | None,
) -> DiscreteColorScale[Any]:
    """Build a DiscreteColorScale for one metadata key across all collection samples."""
    if metadata_type == "string":
        str_values = sorted(set(sample_to_value.values()))
        return DiscreteColorScale.from_values(values=str_values)
    if metadata_type == "boolean":
        return DiscreteColorScale.from_values(
            values=[False, True],
            format_fn=lambda v: "true" if v else "false",
        )
    if metadata_type == "integer":
        return DiscreteColorScale.from_integers(values=(int(v) for v in sample_to_value.values()))

    raise ValueError(
        f"Metadata field '{key}' has unsupported type {metadata_type!r}. "
        "Only 'string', 'boolean', and 'integer' fields can be used for coloring."
    )
