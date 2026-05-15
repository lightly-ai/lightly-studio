"""Metadata-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Union, cast
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable

# Integer fields with more distinct values than this are grouped into buckets
# instead of receiving one category per value.
_INT_CATEGORY_THRESHOLD = 50

_MetadataValueType = type[Union[str, bool, int]]


@dataclass(frozen=True)
class IntBucket:
    """A half-open integer interval [start, end) mapped to a category index."""

    start: int
    end: int
    cat: int


@dataclass(frozen=True)
class MetadataColorScale:
    """Lookup maps built from metadata fields for per-sample color assignment."""

    value_to_category: dict[str, int]
    int_buckets: list[IntBucket]
    legend: dict[int, str]


def build_metadata_color_maps(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    key: str,
    sample_ids: list[UUID],
    fulfils_filter: list[int],
    start_cat: int,
) -> tuple[list[int], dict[int, str]]:
    """Assign a color category to each sample based on a metadata field.

    Returns:
        Tuple of (color_categories, legend) where legend excludes the reserved
        categories (0 = filtered out, 1 = unassigned).
    """
    sample_to_data = _get_collection_metadata(session=session, collection_id=collection_id)
    scale = _build_metadata_color_scale(key=key, sample_to_data=sample_to_data, start_cat=start_cat)
    color_categories = _assign_sample_categories(
        key=key,
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        sample_to_data=sample_to_data,
        scale=scale,
    )
    return color_categories, scale.legend


def _get_collection_metadata(session: Session, collection_id: UUID) -> dict[UUID, dict[str, Any]]:
    """Query all metadata rows for the collection and return a sample_id → data map."""
    rows = session.exec(
        select(SampleMetadataTable)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    ).all()
    return {row.sample_id: row.data for row in rows}


def _build_metadata_color_scale(
    key: str,
    sample_to_data: dict[UUID, dict[str, Any]],
    start_cat: int,
) -> MetadataColorScale:
    """Build a MetadataColorScale for one metadata key across all collection samples."""
    values, value_type = _collect_key_values(key=key, sample_to_data=sample_to_data)
    return _build_color_scale(values=values, value_type=value_type, start_cat=start_cat)


def _assign_sample_categories(
    key: str,
    sample_ids: list[UUID],
    fulfils_filter: list[int],
    sample_to_data: dict[UUID, dict[str, Any]],
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
            key=key,
            sample_to_data=sample_to_data,
            scale=scale,
        )
        color_categories.append(cat if cat is not None else 1)
    return color_categories


def _collect_key_values(
    key: str, sample_to_data: dict[UUID, dict[str, Any]]
) -> tuple[set[str | bool | int], _MetadataValueType | None]:
    """Collect values for one metadata key and enforce a single stored type."""
    values: set[str | bool | int] = set()
    value_type: _MetadataValueType | None = None
    for data in sample_to_data.values():
        val = data.get(key)
        current_type = _get_metadata_value_type(val)
        if current_type is None:
            msg = f"Metadata field '{key}' has unsupported value type {type(val).__name__!r}."
            raise ValueError(msg)
        if value_type is None:
            value_type = current_type
        elif current_type is not value_type:
            raise ValueError(f"Metadata field '{key}' contains mixed value types.")
        assert val is not None
        values.add(val)
    return values, value_type


def _assign_int_categories(
    int_vals: set[int], start_cat: int
) -> tuple[dict[str, int], list[IntBucket], dict[int, str]]:
    """Assign categories to integer values, bucketing when there are too many.

    Returns:
        Tuple of (value_to_category, int_buckets, legend).
    """
    value_to_category: dict[str, int] = {}
    legend: dict[int, str] = {}
    int_buckets: list[IntBucket] = []
    cat = start_cat
    if len(int_vals) <= _INT_CATEGORY_THRESHOLD:
        for iv in sorted(int_vals):
            label = str(iv)
            value_to_category[label] = cat
            legend[cat] = label
            cat += 1
    else:
        for istart, iend, blabel in _make_int_buckets(int_values=int_vals):
            int_buckets.append(IntBucket(start=istart, end=iend, cat=cat))
            legend[cat] = blabel
            cat += 1
    return value_to_category, int_buckets, legend


def _build_color_scale(
    values: set[str | bool | int],
    value_type: _MetadataValueType | None,
    start_cat: int,
) -> MetadataColorScale:
    """Build a MetadataColorScale for one metadata key based on its stored type."""
    value_to_category: dict[str, int] = {}
    legend: dict[int, str] = {}
    cat = start_cat
    if value_type is str:
        str_values = cast(set[str], values)
        for s in sorted(str_values):
            value_to_category[s] = cat
            legend[cat] = s
            cat += 1
        return MetadataColorScale(
            value_to_category=value_to_category, int_buckets=[], legend=legend
        )
    if value_type is bool:
        bool_values = cast(set[bool], values)
        for b in sorted(bool_values):  # False < True
            label = str(b).lower()
            value_to_category[str(b)] = cat
            legend[cat] = label
            cat += 1
        return MetadataColorScale(
            value_to_category=value_to_category, int_buckets=[], legend=legend
        )
    if value_type is int:
        int_values = cast(set[int], values)
        int_value_to_category, int_buckets, int_legend = _assign_int_categories(
            int_vals=int_values, start_cat=cat
        )
        return MetadataColorScale(
            value_to_category=int_value_to_category, int_buckets=int_buckets, legend=int_legend
        )
    return MetadataColorScale(value_to_category=value_to_category, int_buckets=[], legend=legend)


def _get_metadata_value_type(val: Any) -> _MetadataValueType | None:
    """Return the supported metadata value type for coloring."""
    if isinstance(val, str):
        return str
    if isinstance(val, bool):
        return bool
    if isinstance(val, int):
        return int
    return None


def _make_int_buckets(int_values: set[int]) -> list[tuple[int, int, str]]:
    """Create (start_inclusive, end_exclusive, label) bucket tuples for integer values.

    Produces at most _INT_CATEGORY_THRESHOLD buckets with a rounded bucket size.
    """
    min_val = min(int_values)
    max_val = max(int_values)
    val_range = max_val - min_val + 1
    raw_size = math.ceil(val_range / _INT_CATEGORY_THRESHOLD)
    magnitude = 10 ** max(0, math.floor(math.log10(raw_size)))
    bucket_size = math.ceil(raw_size / magnitude) * magnitude

    buckets: list[tuple[int, int, str]] = []
    start = (min_val // bucket_size) * bucket_size
    while start <= max_val:
        end = start + bucket_size
        buckets.append((start, end, f"{start}-{end}"))
        start = end
    return buckets


def _find_metadata_category(
    sample_id: UUID,
    key: str,
    sample_to_data: dict[UUID, dict[str, Any]],
    scale: MetadataColorScale,
) -> int | None:
    """Return the color category for the metadata field, or None."""
    val = sample_to_data.get(sample_id, {}).get(key)
    if isinstance(val, (str, bool)):
        return scale.value_to_category.get(str(val))
    if isinstance(val, int):
        if scale.int_buckets:
            return _lookup_in_int_buckets(val=val, scale=scale)
        return scale.value_to_category.get(str(val))
    return None


def _lookup_in_int_buckets(
    val: int,
    scale: MetadataColorScale,
) -> int | None:
    """Return the category for an integer value via bucket scan."""
    for bucket in scale.int_buckets:
        if bucket.start <= val < bucket.end:
            return bucket.cat
    return None
