"""Resolver for the joint distribution of two sample metadata keys."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import Integer, case, cast, func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select

from lightly_studio.database import db_json
from lightly_studio.models.metadata import (
    CATEGORICAL_TYPE_NAMES,
    NUMERIC_TYPE_NAMES,
    MetadataJointAxisBucketView,
    MetadataJointAxisView,
    MetadataJointDistributionView,
    SampleMetadataTable,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.sample import (
    categorical_value_counts,
    get_metadata_info,
    metadata_helpers,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

DEFAULT_JOINT_BIN_COUNT = 10
DEFAULT_JOINT_VALUE_LIMIT = 20

# Bucket index for rows that belong to no bucket of an axis.
_NO_BUCKET_INDEX = -1


@dataclass(frozen=True)
class _AxisContext:
    """The inputs that every axis of one joint distribution shares."""

    session: Session
    collection_id: UUID
    schema: dict[str, str]
    numeric_stats: dict[str, get_metadata_info.NumericMetadataStats]
    bin_count: int
    limit: int


@dataclass(frozen=True)
class _Axis:
    """An axis of a joint distribution and the SQL that puts each sample in a bucket."""

    view: MetadataJointAxisView
    index_expr: ColumnElement[int]
    # Rows that do not match this condition are not counted. None counts every row.
    condition: ColumnElement[bool] | None


def get_metadata_joint_distribution(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    x_key: str,
    y_key: str,
    filters: ImageFilter | VideoFilter | None = None,
    bin_count: int = DEFAULT_JOINT_BIN_COUNT,
    limit: int = DEFAULT_JOINT_VALUE_LIMIT,
) -> MetadataJointDistributionView:
    """Count the samples for each pair of buckets of two metadata keys.

    The axes always describe the full (unfiltered) collection, so they stay stable
    while the filters change. The metadata filters of both keys are excluded from the
    counts (faceted-search behavior), and all other filters apply.

    A categorical key (``string`` or ``boolean``) has one bucket for each of its
    ``limit`` most frequent values, then an ``other`` and a ``missing`` bucket when
    they are not empty. An ``integer`` key has integer-aligned buckets that include
    both bounds, one bucket per value when the value range allows it. A ``float`` key
    has ``bin_count`` equal-width buckets. Samples without a numeric value are not
    counted.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        x_key: The metadata key of the horizontal axis.
        y_key: The metadata key of the vertical axis.
        filters: Optional sample filters restricting which samples are counted.
        bin_count: The maximum number of buckets of a numeric axis.
        limit: The maximum number of value buckets of a categorical axis.

    Returns:
        The two axes and the sample count of each bucket pair.

    Raises:
        ValueError: If the keys are equal, unknown, without values, or of a type
            that has no distribution.
    """
    if x_key == y_key:
        raise ValueError("The two axes of a joint distribution must use different metadata keys.")
    schema = metadata_helpers.get_merged_schema(session=session, collection_id=collection_id)
    context = _AxisContext(
        session=session,
        collection_id=collection_id,
        schema=schema,
        numeric_stats=get_metadata_info.get_metadata_min_max_counts(
            session=session,
            collection_id=collection_id,
            metadata_keys=[key for key in (x_key, y_key) if schema.get(key) in NUMERIC_TYPE_NAMES],
        ),
        bin_count=bin_count,
        limit=limit,
    )
    x_axis = _build_axis(context=context, key=x_key)
    y_axis = _build_axis(context=context, key=y_key)
    axis_filters = metadata_helpers.without_metadata_key_filter(
        filters=metadata_helpers.without_metadata_key_filter(filters=filters, metadata_key=x_key),
        metadata_key=y_key,
    )
    counts = _count_bucket_pairs(
        session=session,
        collection_id=collection_id,
        x_axis=x_axis,
        y_axis=y_axis,
        filters=axis_filters,
    )
    return MetadataJointDistributionView(x_axis=x_axis.view, y_axis=y_axis.view, counts=counts)


def _build_axis(context: _AxisContext, key: str) -> _Axis:
    metadata_type = context.schema.get(key)
    if metadata_type is None:
        raise ValueError(f"Unknown metadata key {key!r}.")
    if metadata_type in CATEGORICAL_TYPE_NAMES:
        return _build_categorical_axis(context=context, key=key, metadata_type=metadata_type)
    if metadata_type not in NUMERIC_TYPE_NAMES:
        raise ValueError(f"Metadata key {key!r} of type {metadata_type!r} has no distribution.")
    stats = context.numeric_stats.get(key)
    if stats is None:
        raise ValueError(f"Metadata key {key!r} has no values.")
    if metadata_type == "integer":
        return _build_integer_axis(key=key, stats=stats, bin_count=context.bin_count)
    return _build_float_axis(key=key, stats=stats, bin_count=context.bin_count)


def _build_categorical_axis(context: _AxisContext, key: str, metadata_type: str) -> _Axis:
    """Build the value, ``other`` and ``missing`` buckets of a categorical key."""
    text_expr = db_json.json_extract_key_as_text(column=SampleMetadataTable.data, key=key)
    grouped = categorical_value_counts.get_top_value_counts(
        session=context.session,
        collection_id=context.collection_id,
        value_expr=text_expr,
        filters=None,
        limit=context.limit,
    )
    # The NULL group can be part of the top groups. It is the missing bucket instead.
    top_values = [row.value for row in grouped.values if row.value is not None]
    top_count = sum(row.count for row in grouped.values if row.value is not None)
    other_count = grouped.total_count - grouped.missing_count - top_count
    buckets = [
        MetadataJointAxisBucketView(
            kind="value",
            value=categorical_value_counts.parse_value(value=value, metadata_type=metadata_type),
        )
        for value in top_values
    ]
    other_index = _append_bucket(buckets=buckets, kind="other", is_empty=other_count == 0)
    missing_index = _append_bucket(
        buckets=buckets, kind="missing", is_empty=grouped.missing_count == 0
    )
    # The NULL branch comes first, else a NULL value falls into the "other" bucket.
    index_expr = case(
        (text_expr.is_(None), missing_index),
        *[(text_expr == value, index) for index, value in enumerate(top_values)],
        else_=other_index,
    )
    return _Axis(
        view=MetadataJointAxisView(key=key, type=metadata_type, buckets=buckets),
        index_expr=index_expr,
        condition=None,
    )


def _build_integer_axis(
    key: str, stats: get_metadata_info.NumericMetadataStats, bin_count: int
) -> _Axis:
    """Build integer-aligned buckets that include both bounds.

    The width is the smallest integer that keeps the bucket count at most
    ``bin_count``, so a key with a small value range gets one bucket per value.
    """
    min_value = int(stats.min_value)
    max_value = int(stats.max_value)
    width = max(1, math.ceil((max_value - min_value + 1) / bin_count))
    bucket_count = (max_value - min_value) // width + 1
    buckets = [
        MetadataJointAxisBucketView(
            kind="range",
            min=min_value + index * width,
            max=min(min_value + (index + 1) * width - 1, max_value),
        )
        for index in range(bucket_count)
    ]
    value_expr = db_json.json_extract_key_as_float(column=SampleMetadataTable.data, key=key)
    # Floor before the cast, because a cast to integer rounds.
    index_expr = cast(func.floor((value_expr - min_value) / width), Integer)
    return _Axis(
        view=MetadataJointAxisView(key=key, type="integer", buckets=buckets),
        index_expr=index_expr,
        condition=_numeric_value_not_null(key=key),
    )


def _build_float_axis(
    key: str, stats: get_metadata_info.NumericMetadataStats, bin_count: int
) -> _Axis:
    """Build equal-width buckets with the same edges as the metadata histogram."""
    min_value = stats.min_value
    max_value = stats.max_value
    # All values are equal: one bucket holds every value.
    bucket_count = bin_count if max_value > min_value else 1
    width = (max_value - min_value) / bucket_count if max_value > min_value else 1.0
    value_range = max_value - min_value
    edges = [min_value + value_range * index / bucket_count for index in range(bucket_count + 1)]
    # Guard against float drift so the last edge is exactly the max value.
    edges[-1] = max_value
    buckets = [
        MetadataJointAxisBucketView(kind="range", min=edges[index], max=edges[index + 1])
        for index in range(bucket_count)
    ]
    value_expr = db_json.json_extract_key_as_float(column=SampleMetadataTable.data, key=key)
    # Values equal to the max fall into the last bucket.
    raw_index = cast(func.floor((value_expr - min_value) / width), Integer)
    index_expr = func.least(func.greatest(raw_index, 0), bucket_count - 1)
    return _Axis(
        view=MetadataJointAxisView(key=key, type="float", buckets=buckets),
        index_expr=index_expr,
        condition=_numeric_value_not_null(key=key),
    )


def _count_bucket_pairs(
    session: Session,
    collection_id: UUID,
    x_axis: _Axis,
    y_axis: _Axis,
    filters: ImageFilter | VideoFilter | None,
) -> list[list[int]]:
    """Count the samples of each bucket pair, as ``counts[y_index][x_index]``."""
    conditions = [axis.condition for axis in (x_axis, y_axis) if axis.condition is not None]
    # The bucket indices come from a subquery, and the outer query groups by its
    # columns. Grouping by the index expressions directly fails on DuckDB.
    pairs_query = (
        select(x_axis.index_expr.label("x_index"), y_axis.index_expr.label("y_index"))
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
            isouter=True,
        )
        .where(col(SampleTable.collection_id) == collection_id, *conditions)
    )
    pairs_query = metadata_helpers.apply_collection_filter(
        query=pairs_query, collection_id=collection_id, filters=filters
    )
    pairs = pairs_query.subquery()
    count_query = select(pairs.c.x_index, pairs.c.y_index, func.count()).group_by(
        pairs.c.x_index, pairs.c.y_index
    )
    x_count = len(x_axis.view.buckets)
    y_count = len(y_axis.view.buckets)
    counts = [[0] * x_count for _ in range(y_count)]
    for x_index, y_index, count in session.execute(count_query):
        if 0 <= x_index < x_count and 0 <= y_index < y_count:
            counts[y_index][x_index] = int(count)
    return counts


def _append_bucket(
    buckets: list[MetadataJointAxisBucketView],
    kind: Literal["other", "missing"],
    is_empty: bool,
) -> int:
    """Append an aggregate bucket unless it is empty, and return its index."""
    if is_empty:
        return _NO_BUCKET_INDEX
    buckets.append(MetadataJointAxisBucketView(kind=kind))
    return len(buckets) - 1


def _numeric_value_not_null(key: str) -> ColumnElement[bool]:
    return db_json.json_extract_key_as_text(column=SampleMetadataTable.data, key=key).isnot(None)
