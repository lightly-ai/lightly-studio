"""Metadata-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.resolvers.metadata_resolver import sample as sample_metadata_resolver


def build_metadata_color_maps(
    session: Session,
    collection_id: UUID,
    key: str,
    sample_ids: list[UUID],
    matching_sample_ids: set[UUID] | None,
) -> tuple[list[list[int]], dict[int, str]]:
    """Build color categories and a legend for metadata-based sample coloring.

    A metadata key holds a single value per sample, so each sample maps to a
    single-element category list. The list shape keeps this consistent with the
    other coloring sources (e.g. tags, annotations).

    Args:
        session: Database session.
        collection_id: ID of the collection whose metadata should be used.
        key: Metadata field used for coloring.
        sample_ids: Sample IDs in the order for which to build color categories.
        matching_sample_ids: Sample IDs matching the active filter. String and
            boolean values are prioritized by their frequency among these samples
            so the legend reflects the filtered view. ``None`` counts all samples.

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
        matching_sample_ids=matching_sample_ids,
    )
    categories = []
    for sample_id in sample_ids:
        value = sample_to_value.get(sample_id)
        category = scale.value_to_category(value) if value is not None else None
        categories.append([category] if category is not None else [])
    return categories, scale.legend


def _build_metadata_color_scale(
    key: str,
    sample_to_value: dict[UUID, Any],
    metadata_type: str | None,
    matching_sample_ids: set[UUID] | None,
) -> DiscreteColorScale[Any]:
    """Build a DiscreteColorScale for one metadata key.

    For string and boolean fields, when there are more values than fit in the
    legend, the values most common among the filter-matching samples each get a
    dedicated color category and the rest are merged into a single "Other"
    category; values absent from the matching samples are omitted. Integer values
    use fixed-range bucketing and stay filter-independent.
    """
    if metadata_type in ("string", "boolean"):
        format_fn: Callable[[Any], str] = (
            (lambda v: "true" if v else "false") if metadata_type == "boolean" else str
        )
        counts = Counter(
            value
            for sid, value in sample_to_value.items()
            if matching_sample_ids is None or sid in matching_sample_ids
        )
        ordered_values = sorted(counts, key=lambda value: (-counts[value], format_fn(value)))
        return DiscreteColorScale.from_values(values=ordered_values, format_fn=format_fn)
    if metadata_type == "integer":
        return DiscreteColorScale.from_integers(values=(int(v) for v in sample_to_value.values()))

    raise ValueError(
        f"Metadata field '{key}' has unsupported type {metadata_type!r}. "
        "Only 'string', 'boolean', and 'integer' fields can be used for coloring."
    )
