"""Resolver for categorical sample metadata value counts."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

import sqlalchemy
import sqlmodel
from sqlalchemy import func, true
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

    Each field's own metadata filter is excluded while all other filters apply
    (faceted-search behavior).  Results contain the 20 most frequent concrete
    values, followed by an ``__other__`` row aggregating the less frequent
    concrete values and a ``__missing__`` row counting the samples with an absent
    or null value.  Both aggregate rows are omitted when their count is zero, so
    the counts always sum to the number of samples in scope.

    Fields that share the same effective filter set are aggregated in a single
    database query, so the number of round-trips is bounded by the number of
    distinct active metadata filters rather than the total number of fields.

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
    categorical_fields = [
        key
        for key, metadata_type in schema.items()
        if metadata_type in CATEGORICAL_TYPE_NAMES and (fields is None or key in fields)
    ]

    # Group fields by their effective filter set. Fields whose own key is not
    # present in any active metadata filter all share the baseline filter and are
    # queried together. Fields whose key IS actively filtered each need the
    # baseline minus that one filter, so they form their own singleton group.
    groups: dict[frozenset[str], list[str]] = defaultdict(list)
    for key in categorical_fields:
        field_filters = metadata_helpers.without_metadata_key_filter(
            filters=filters, metadata_key=key
        )
        # Use the remaining metadata filter keys as the group identity. Two fields
        # share a group iff their effective filter sets are identical.
        active_keys = _active_metadata_filter_keys(field_filters)
        groups[active_keys].append(key)

    result: dict[str, MetadataValueCountsView] = {}
    for _active_keys, group_fields in groups.items():
        # Reconstruct the shared filter for this group from the first field
        # (all fields in the group have the same effective filter).
        group_filters = metadata_helpers.without_metadata_key_filter(
            filters=filters, metadata_key=group_fields[0]
        )
        # Total count must use the same effective filter as the value query so that
        # __missing__ = total - non_null stays non-negative. Using the original
        # filter here would exclude samples the value query includes (e.g. city=A
        # would hide city=B samples from the total but not from the city value query).
        group_total = _get_total_count(
            session=session, collection_id=collection_id, filters=group_filters
        )
        raw_counts = _query_value_counts(
            session=session,
            collection_id=collection_id,
            keys=group_fields,
            filters=group_filters,
        )
        for key in group_fields:
            key_counts = raw_counts.get(key, {})
            result[key] = _build_value_counts_view(
                key_counts=key_counts,
                metadata_type=schema[key],
                total_count=group_total,
            )

    return result


def _query_value_counts(
    session: Session,
    collection_id: UUID,
    keys: list[str],
    filters: ImageFilter | None,
) -> dict[str, dict[str | None, int]]:
    """Aggregate value counts for all ``keys`` in a single query.

    Returns a nested mapping of ``{key: {value_or_None: count}}``.  SQL NULL
    values (absent or JSON-null fields) map to ``None`` in the inner dict.
    """
    # Compile the metadata column reference for the dialect so that
    # json_object_unnest_lateral can embed it in the correct raw SQL fragment.
    bind = session.get_bind()
    data_col = sqlalchemy.inspect(SampleMetadataTable).mapper.column_attrs["data"].columns[0]
    data_col_sql = str(data_col.compile(dialect=bind.dialect))
    # Lateral unnest expands each sample's JSON object into (key, value) rows.
    # Both dialects expose a "key" text column and a "value" text column (SQL NULL
    # for JSON null); see json_object_unnest_lateral in db_json for per-dialect SQL.
    kv = db_json.json_object_unnest_lateral(column_sql=data_col_sql, dialect_name=bind.dialect.name)
    kv_key = kv.c.key
    kv_value = kv.c.value

    count_expr = func.count().label("cnt")
    query = (
        sqlmodel.select(kv_key.label("key"), kv_value.label("val"), count_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            sqlmodel.col(SampleMetadataTable.sample_id) == sqlmodel.col(SampleTable.sample_id),
            isouter=True,
        )
        .join(kv, true())
        .where(SampleTable.collection_id == collection_id)
        .where(kv_key.in_(keys))
        .group_by(kv_key, kv_value)
    )
    query = metadata_helpers.apply_image_filters(
        query=query, collection_id=collection_id, filters=filters
    )

    result: dict[str, dict[str | None, int]] = defaultdict(dict)
    for key, val, count in session.execute(query).all():
        result[str(key)][val] = int(count)
    return result


def _get_total_count(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None,
) -> int:
    """Return the total number of samples in scope under ``filters``."""
    query = (
        sqlmodel.select(func.count())
        .select_from(SampleTable)
        .where(SampleTable.collection_id == collection_id)
    )
    query = metadata_helpers.apply_image_filters(
        query=query, collection_id=collection_id, filters=filters
    )
    return int(session.execute(query).scalar_one())


def _build_value_counts_view(
    key_counts: dict[str | None, int],
    metadata_type: str,
    total_count: int,
) -> MetadataValueCountsView:
    """Build the value-counts view for one field from raw aggregation results.

    Takes the top-20 concrete values, then appends ``__other__`` and
    ``__missing__`` aggregates when their counts are non-zero.

    Args:
        key_counts: Mapping from raw string value (or None for SQL NULL) to count.
        metadata_type: The schema type name of this field (e.g. ``"string"``).
        total_count: Total samples in scope, used to compute the missing count.

    Returns:
        The assembled view for this field.
    """
    # Separate NULL (missing) from concrete values.
    missing_count = key_counts.get(None, 0)
    concrete: list[tuple[str, int]] = [
        (val, cnt) for val, cnt in key_counts.items() if val is not None
    ]
    concrete.sort(key=lambda pair: (-pair[1], pair[0]))

    top = concrete[:_TOP_VALUE_COUNT]
    other_count = sum(cnt for _, cnt in concrete[_TOP_VALUE_COUNT:])

    # Samples with no metadata row at all are not in key_counts; add them to missing.
    non_null_count = sum(cnt for _, cnt in concrete)
    missing_count = total_count - non_null_count

    value_counts = [
        MetadataValueCountView(
            value=_parse_value(value=val, metadata_type=metadata_type), count=cnt
        )
        for val, cnt in top
    ]
    if other_count > 0:
        value_counts.append(MetadataValueCountView(value=_OTHER_VALUE_SENTINEL, count=other_count))
    if missing_count > 0:
        value_counts.append(
            MetadataValueCountView(value=_MISSING_VALUE_SENTINEL, count=missing_count)
        )
    return MetadataValueCountsView(value_counts=value_counts)


def _active_metadata_filter_keys(filters: ImageFilter | None) -> frozenset[str]:
    """Return the set of metadata filter keys active in ``filters``."""
    if (
        filters is None
        or filters.sample_filter is None
        or not filters.sample_filter.metadata_filters
    ):
        return frozenset()
    return frozenset(f.key for f in filters.sample_filter.metadata_filters)


def _parse_value(value: str, metadata_type: str) -> str | bool:
    if metadata_type == "boolean":
        return value.lower() == "true"
    return value
