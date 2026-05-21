"""Metadata-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import coloring_helpers
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.resolvers.metadata_resolver import sample as sample_metadata_resolver

_MAX_INTEGER_CATEGORIES = 50


def build_metadata_color_maps(
    session: Session,
    collection_id: UUID,
    key: str,
    sample_ids: list[UUID],
    fulfils_filter: list[int],
) -> tuple[list[int], dict[int, str]]:
    """Build color categories and a legend for metadata-based sample coloring.

    Args:
        session: Database session.
        collection_id: ID of the collection whose metadata should be used.
        key: Metadata field used for coloring.
        sample_ids: Sample IDs in the order for which to build color categories.
        fulfils_filter: Per-sample filter flags where 0 means filtered out and 1
            means the sample fulfils the filter.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples. The
        length of `color_categories` is the number of samples. The `color_legend` is a mapping
        from color ID to a human-readable string.
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
    return coloring_helpers.assign_color_categories(
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        sample_to_value=sample_to_value,
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
        return _build_integer_color_scale(sample_to_value)

    raise ValueError(
        f"Metadata field '{key}' has unsupported type {metadata_type!r}. "
        "Only 'string', 'boolean', and 'integer' fields can be used for coloring."
    )


def _build_integer_color_scale(
    sample_to_value: dict[UUID, Any],
) -> DiscreteColorScale[int]:
    """Build a color scale for an integer metadata field.

    When the number of unique values is at most ``_MAX_INTEGER_CATEGORIES``, each
    unique value gets its own category.  Otherwise the range [min, max] is split
    into at most ``_MAX_INTEGER_CATEGORIES`` equal-width buckets and each sample is
    mapped to the bucket that contains its value.

    In both cases categories are ordered numerically (smallest value first).
    """
    unique_values = sorted({int(v) for v in sample_to_value.values()})

    if len(unique_values) <= _MAX_INTEGER_CATEGORIES:
        return DiscreteColorScale.from_values(values=unique_values)

    # Bucket into at most _MAX_INTEGER_CATEGORIES ranges.
    min_val = unique_values[0]
    max_val = unique_values[-1]
    value_range = max_val - min_val
    # Round bucket width up to a "nice" power-of-ten multiple so labels are readable.
    raw_width = value_range / _MAX_INTEGER_CATEGORIES
    magnitude = 10 ** math.floor(math.log10(raw_width)) if raw_width >= 1 else 1
    bucket_width = math.ceil(raw_width / magnitude) * magnitude

    num_buckets = math.ceil((value_range + 1) / bucket_width)

    def _bucket_idx(value: int) -> int:
        return min((value - min_val) // bucket_width, num_buckets - 1)

    def _label(bucket_start: int) -> str:
        return f"{bucket_start}-{bucket_start + bucket_width - 1}"

    legend: dict[int, str] = {2 + i: _label(min_val + i * bucket_width) for i in range(num_buckets)}
    lookup: dict[int, int] = {v: 2 + _bucket_idx(v) for v in unique_values}

    return DiscreteColorScale.from_lookup(lookup=lookup, legend=legend)
