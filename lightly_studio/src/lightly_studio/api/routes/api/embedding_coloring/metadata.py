"""Metadata-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.metadata import (
    NAME_TO_TYPE_MAP,
)
from lightly_studio.resolvers.metadata_resolver import sample as sample_metadata_resolver

_SUPPORTED_TYPE_NAMES = frozenset({"string", "boolean"})


@dataclass(frozen=True)
class MetadataColorScale:
    """Lookup maps built from metadata fields for per-sample color assignment."""

    value_to_category: dict[str, int]
    legend: dict[int, str]


def build_metadata_color_maps(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    key: str,
    sample_ids: list[UUID],
    fulfils_filter: list[int],
    start_cat: int,
) -> tuple[list[int], dict[int, str]]:
    """Build color categories and a legend for metadata-based sample coloring.

    The legend excludes the reserved categories (0 = filtered out,
    1 = unassigned).

    Args:
        session: Database session.
        collection_id: ID of the collection whose metadata should be used.
        key: Metadata field used for coloring.
        sample_ids: Sample IDs in the order for which to build color categories.
        fulfils_filter: Per-sample filter flags where 0 means filtered out and 1
            means the sample fulfils the filter.
        start_cat: First category ID available for metadata values, usually 2 to
            reserve, 0 for filtered-out samples and 1 for unassigned samples.

    Returns:
        Tuple of color categories per sample and the legend for metadata values.
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
        start_cat=start_cat,
    )
    color_categories = _assign_sample_categories(
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        sample_to_value=sample_to_value,
        scale=scale,
    )
    return color_categories, scale.legend


def _build_metadata_color_scale(
    key: str,
    sample_to_value: dict[UUID, Any],
    metadata_type: str | None,
    start_cat: int,
) -> MetadataColorScale:
    """Build a MetadataColorScale for one metadata key across all collection samples."""
    if metadata_type not in _SUPPORTED_TYPE_NAMES:
        raise ValueError(
            f"Metadata field '{key}' has unsupported type {metadata_type!r}. "
            "Only 'string' and 'boolean' fields can be used for coloring."
        )
    values = set(sample_to_value.values())
    value_type = cast("type[str | bool]", NAME_TO_TYPE_MAP[metadata_type])
    if value_type is str:
        return _build_color_scale_str(values=cast(set[str], values), start_cat=start_cat)
    return _build_color_scale_bool(values=cast(set[bool], values), start_cat=start_cat)


def _assign_sample_categories(
    sample_ids: list[UUID],
    fulfils_filter: list[int],
    sample_to_value: dict[UUID, Any],
    scale: MetadataColorScale,
) -> list[int]:
    """Return a color category per sample (0 = filtered out, 1 = unassigned)."""
    color_categories: list[int] = []
    for i, sample_id in enumerate(sample_ids):
        if fulfils_filter[i] == 0:
            color_categories.append(0)
            continue
        cat = _find_metadata_category(
            sample_id=sample_id,
            sample_to_value=sample_to_value,
            scale=scale,
        )
        color_categories.append(cat if cat is not None else 1)
    return color_categories


def _build_color_scale_str(
    values: set[str],
    start_cat: int,
) -> MetadataColorScale:
    """Build a MetadataColorScale for string metadata values."""
    value_to_category: dict[str, int] = {}
    legend: dict[int, str] = {}
    cat = start_cat
    for value in sorted(values):
        value_to_category[value] = cat
        legend[cat] = value
        cat += 1
    return MetadataColorScale(value_to_category=value_to_category, legend=legend)


def _build_color_scale_bool(
    values: set[bool],
    start_cat: int,
) -> MetadataColorScale:
    """Build a MetadataColorScale for boolean metadata values."""
    value_to_category: dict[str, int] = {}
    legend: dict[int, str] = {}
    cat = start_cat
    for value in sorted(values):
        label = str(value).lower()
        value_to_category[str(value)] = cat
        legend[cat] = label
        cat += 1
    return MetadataColorScale(value_to_category=value_to_category, legend=legend)


def _find_metadata_category(
    sample_id: UUID,
    sample_to_value: dict[UUID, Any],
    scale: MetadataColorScale,
) -> int | None:
    """Return the color category for the metadata field, or None."""
    val = sample_to_value.get(sample_id)
    if isinstance(val, (str, bool)):
        return scale.value_to_category.get(str(val))
    return None
