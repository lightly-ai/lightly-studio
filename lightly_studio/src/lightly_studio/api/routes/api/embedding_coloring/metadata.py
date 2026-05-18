"""Metadata-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.metadata import (
    NAME_TO_TYPE_MAP,
    SampleMetadataTable,
    validate_type_compatibility,
)
from lightly_studio.models.sample import SampleTable

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
        fulfils_filter: Per-sample filter flags where 0 means filtered out.
        start_cat: First category ID available for metadata values.

    Returns:
        Tuple of color categories per sample and the legend for metadata values.
    """
    sample_to_data, metadata_schema = _get_collection_metadata(
        session=session, collection_id=collection_id
    )
    scale = _build_metadata_color_scale(
        key=key, sample_to_data=sample_to_data, metadata_schema=metadata_schema, start_cat=start_cat
    )
    color_categories = _assign_sample_categories(
        key=key,
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        sample_to_data=sample_to_data,
        scale=scale,
    )
    return color_categories, scale.legend


def _get_collection_metadata(
    session: Session, collection_id: UUID
) -> tuple[dict[UUID, dict[str, Any]], dict[str, str]]:
    """Query all metadata rows for the collection.

    Returns:
        Tuple of (sample_id -> data map, merged metadata schema).
    """
    rows = session.exec(
        select(SampleMetadataTable)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    ).all()
    merged_schema: dict[str, str] = {}
    for row in rows:
        for key, typ in row.metadata_schema.items():
            existing_type = merged_schema.get(key)
            if existing_type is None:
                merged_schema[key] = typ
                continue
            if existing_type != typ:
                raise ValueError(
                    f"Metadata field '{key}': value does not match schema type {existing_type!r}."
                )

    return {row.sample_id: row.data for row in rows}, merged_schema


def _build_metadata_color_scale(
    key: str,
    sample_to_data: dict[UUID, dict[str, Any]],
    metadata_schema: dict[str, str],
    start_cat: int,
) -> MetadataColorScale:
    """Build a MetadataColorScale for one metadata key across all collection samples."""
    values = _collect_key_values(
        key=key, sample_to_data=sample_to_data, metadata_schema=metadata_schema
    )
    value_type = cast("type[str | bool]", NAME_TO_TYPE_MAP[metadata_schema[key]])
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
    key: str,
    sample_to_data: dict[UUID, dict[str, Any]],
    metadata_schema: dict[str, str],
) -> set[str | bool]:
    """Collect values for one metadata key, validating against the schema type."""
    type_name = metadata_schema.get(key)
    if type_name not in _SUPPORTED_TYPE_NAMES:
        raise ValueError(
            f"Metadata field '{key}' has unsupported type {type_name!r}. "
            "Only 'string' and 'boolean' fields can be used for coloring."
        )
    values: set[str | bool] = set()
    for data in sample_to_data.values():
        val = data.get(key)
        if val is None:
            continue
        if not validate_type_compatibility(type_name, val):
            raise ValueError(
                f"Metadata field '{key}': value {val!r} does not match schema type {type_name!r}."
            )
        values.add(val)
    return values


def _build_color_scale(
    values: set[str | bool],
    value_type: type[str | bool] | None,
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
        return MetadataColorScale(value_to_category=value_to_category, legend=legend)

    bool_values = cast(set[bool], values)
    for b in sorted(bool_values):
        label = str(b).lower()
        value_to_category[str(b)] = cat
        legend[cat] = label
        cat += 1
    return MetadataColorScale(value_to_category=value_to_category, legend=legend)


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
    return None
