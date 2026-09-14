"""Resolver for categorical sample metadata value counts."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import sqlmodel
from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session

from lightly_studio.database import db_json
from lightly_studio.models.metadata import (
    CATEGORICAL_TYPE_NAMES,
    MetadataValueCountsView,
    MetadataValueCountView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.sample import metadata_helpers

_TOP_VALUE_COUNT = 20

# Aggregate rows appended to the top values so the counts add up to every sample
# in scope. The frontend matches these exact strings to render the "Other" and
# "Missing" buckets, see MISSING_CATEGORICAL_VALUE and OTHER_CATEGORICAL_VALUE in
# lightly_studio_view/src/lib/services/types.ts.
_OTHER_VALUE_SENTINEL = "__other__"
_MISSING_VALUE_SENTINEL = "__missing__"


@dataclass(frozen=True)
class _GroupedValueCount:
    """A grouped metadata value and its count."""

    value: str | None
    count: int


@dataclass(frozen=True)
class _GroupedValueCounts:
    """Grouped values together with totals for the complete result."""

    values: list[_GroupedValueCount]
    total_count: int
    missing_count: int


def get_metadata_value_counts(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None = None,
    fields: list[str] | None = None,
) -> dict[str, MetadataValueCountsView]:
    """Count categorical metadata values for a collection.

    Each field's own metadata filter is excluded while all other filters apply.
    Results contain the 20 most frequent concrete values, followed by an
    ``__other__`` row aggregating the less frequent concrete values and a
    ``__missing__`` row counting the samples with an absent or null value. Both
    aggregate rows are omitted when their count is zero, so the counts always sum
    to the number of samples in scope.

    Args:
        session: The database session.
        collection_id: The collection whose sample metadata is aggregated.
        filters: Optional image filters restricting the counted samples.
        fields: Categorical fields to count. Pass only the fields that will be
            rendered (e.g. on a bar chart) to avoid running DB queries for
            fields whose results would never be used. All categorical fields
            are counted when absent.

    Returns:
        A mapping from categorical metadata keys to their value counts.
    """
    schema = metadata_helpers.get_merged_schema(session=session, collection_id=collection_id)
    result: dict[str, MetadataValueCountsView] = {}
    for key, metadata_type in schema.items():
        if metadata_type not in CATEGORICAL_TYPE_NAMES:
            continue
        if fields is not None and key not in fields:
            continue
        field_filters = metadata_helpers.without_metadata_key_filter(
            filters=filters, metadata_key=key
        )
        result[key] = _get_field_value_counts(
            session=session,
            collection_id=collection_id,
            metadata_key=key,
            metadata_type=metadata_type,
            filters=field_filters,
        )
    return result


def _get_field_value_counts(
    session: Session,
    collection_id: UUID,
    metadata_key: str,
    metadata_type: str,
    filters: ImageFilter | None,
) -> MetadataValueCountsView:
    """Build the response from one grouped query for this metadata field.

    The query returns the most frequent concrete values and window totals for
    all samples in scope. Missing values are kept outside the top-value limit
    so they can be returned as the separate ``__missing__`` bucket.
    """
    value_expr = db_json.json_extract_key_as_text(column=SampleMetadataTable.data, key=metadata_key)
    grouped_counts = _get_top_value_counts(
        session=session,
        collection_id=collection_id,
        value_expr=value_expr,
        filters=filters,
    )
    value_counts = [
        MetadataValueCountView(
            value=_parse_value(value=row.value, metadata_type=metadata_type), count=row.count
        )
        for row in grouped_counts.values
        if row.value is not None
    ]
    total_count = grouped_counts.total_count
    missing_count = grouped_counts.missing_count
    other_count = total_count - missing_count - sum(entry.count for entry in value_counts)
    if other_count > 0:
        value_counts.append(MetadataValueCountView(value=_OTHER_VALUE_SENTINEL, count=other_count))
    if missing_count > 0:
        value_counts.append(
            MetadataValueCountView(value=_MISSING_VALUE_SENTINEL, count=missing_count)
        )
    return MetadataValueCountsView(value_counts=value_counts)


def _get_top_value_counts(
    session: Session,
    collection_id: UUID,
    value_expr: ColumnElement[str],
    filters: ImageFilter | None,
) -> _GroupedValueCounts:
    """Return top concrete groups plus totals from the complete grouped result."""
    count_expr = func.count().label("value_count")
    query = (
        sqlmodel.select(value_expr.label("value"), count_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            sqlmodel.col(SampleMetadataTable.sample_id) == sqlmodel.col(SampleTable.sample_id),
            isouter=True,
        )
        .where(SampleTable.collection_id == collection_id)
        .group_by(value_expr)
    )
    query = metadata_helpers.apply_image_filters(
        query=query, collection_id=collection_id, filters=filters
    )
    grouped = query.subquery()
    value, count = grouped.c.value, grouped.c.value_count
    total_count_expr = func.sum(count).over().label("total_count")
    missing_count_expr = (
        func.sum(case((value.is_(None), count), else_=0)).over().label("missing_count")
    )
    totals_query = sqlmodel.select(
        value,
        count,
        total_count_expr,
        missing_count_expr,
    ).order_by(value.is_(None), count.desc(), value.asc())
    grouped_values: list[_GroupedValueCount] = []
    total_count = 0
    missing_count = 0
    for value, count, total, missing in session.execute(totals_query).fetchmany(_TOP_VALUE_COUNT):
        if not grouped_values:
            total_count = int(total)
            missing_count = int(missing)
        grouped_values.append(
            _GroupedValueCount(
                value=str(value) if value is not None else None,
                count=int(count),
            )
        )
    return _GroupedValueCounts(
        values=grouped_values,
        total_count=total_count,
        missing_count=missing_count,
    )


def _parse_value(value: str, metadata_type: str) -> str | bool:
    if metadata_type == "boolean":
        return value.lower() == "true"
    return value
