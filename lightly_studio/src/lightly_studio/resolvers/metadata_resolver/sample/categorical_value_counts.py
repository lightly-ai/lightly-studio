"""Resolver for categorical sample metadata value counts."""

from __future__ import annotations

from uuid import UUID

import sqlmodel
from sqlalchemy import func
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
    value_expr = db_json.json_extract_key_as_text(column=SampleMetadataTable.data, key=metadata_key)
    rows = _get_top_value_counts(
        session=session,
        collection_id=collection_id,
        value_expr=value_expr,
        filters=filters,
    )
    value_counts = [
        MetadataValueCountView(
            value=_parse_value(value=value, metadata_type=metadata_type), count=int(count)
        )
        for value, count in rows
    ]
    total_count, non_null_count = _get_scope_counts(
        session=session,
        collection_id=collection_id,
        value_expr=value_expr,
        filters=filters,
    )
    # Built here rather than through ``_parse_value``, which would coerce the
    # sentinels to ``False`` on a boolean field.
    other_count = non_null_count - sum(int(count) for _, count in rows)
    if other_count > 0:
        value_counts.append(MetadataValueCountView(value=_OTHER_VALUE_SENTINEL, count=other_count))
    missing_count = total_count - non_null_count
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
) -> list[tuple[str, int]]:
    count_expr = func.count().label("value_count")
    query = (
        sqlmodel.select(value_expr, count_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            sqlmodel.col(SampleMetadataTable.sample_id) == sqlmodel.col(SampleTable.sample_id),
            isouter=True,
        )
        .where(SampleTable.collection_id == collection_id)
        .where(value_expr.isnot(None))
        .group_by(value_expr)
        .order_by(count_expr.desc(), value_expr.asc())
        .limit(_TOP_VALUE_COUNT)
    )
    query = metadata_helpers.apply_image_filters(
        query=query, collection_id=collection_id, filters=filters
    )
    return [(str(value), int(count)) for value, count in session.execute(query).all()]


def _get_scope_counts(
    session: Session,
    collection_id: UUID,
    value_expr: ColumnElement[str],
    filters: ImageFilter | None,
) -> tuple[int, int]:
    """Count the samples in scope and those holding a concrete value.

    Args:
        session: The database session.
        collection_id: The collection whose samples are counted.
        value_expr: Expression extracting the metadata value of the counted field.
        filters: Optional image filters restricting the counted samples. Must be
            the same filters the value counts were taken under, so the totals
            describe the same scope.

    Returns:
        The number of samples in scope and, of those, the number whose value is
        neither absent nor null.
    """
    query = (
        sqlmodel.select(func.count(), func.count(value_expr))
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            sqlmodel.col(SampleMetadataTable.sample_id) == sqlmodel.col(SampleTable.sample_id),
            isouter=True,
        )
        .where(SampleTable.collection_id == collection_id)
    )
    query = metadata_helpers.apply_image_filters(
        query=query, collection_id=collection_id, filters=filters
    )
    total_count, non_null_count = session.execute(query).one()
    return int(total_count), int(non_null_count)


def _parse_value(value: str, metadata_type: str) -> str | bool:
    if metadata_type == "boolean":
        return value.lower() == "true"
    return value
