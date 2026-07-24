"""Resolver for categorical sample metadata value counts."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select

from lightly_studio.database import db_json
from lightly_studio.models.metadata import (
    MetadataValueCountsView,
    MetadataValueCountView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.metadata_resolver.sample import metadata_helpers

if TYPE_CHECKING:
    from lightly_studio.resolvers.image_filter import ImageFilter

_CATEGORICAL_TYPES = ("string", "boolean")
_TOP_VALUE_COUNT = 20


def get_metadata_value_counts(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None = None,
) -> dict[str, MetadataValueCountsView]:
    """Count categorical metadata values for a collection.

    Each field's own metadata filter is excluded while all other filters apply.
    Results contain the 20 most frequent concrete values, with the remaining
    concrete and missing values counted separately.

    Args:
        session: The database session.
        collection_id: The collection whose sample metadata is aggregated.
        filters: Optional image filters restricting the counted samples.

    Returns:
        A mapping from categorical metadata keys to their value counts.
    """
    schema = metadata_helpers.get_merged_schema(session=session, collection_id=collection_id)
    result: dict[str, MetadataValueCountsView] = {}
    for key, metadata_type in schema.items():
        if metadata_type not in _CATEGORICAL_TYPES:
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
    value_expr = db_json.json_extract_string(column=SampleMetadataTable.data, field=metadata_key)
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
    return MetadataValueCountsView(value_counts=value_counts)


def _get_top_value_counts(
    session: Session,
    collection_id: UUID,
    value_expr: ColumnElement[str],
    filters: ImageFilter | None,
) -> list[tuple[str, int]]:
    count_expr = func.count().label("value_count")
    query = (
        select(value_expr, count_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
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


def _parse_value(value: str, metadata_type: str) -> str | bool:
    if metadata_type == "boolean":
        return value.lower() == "true"
    return value
