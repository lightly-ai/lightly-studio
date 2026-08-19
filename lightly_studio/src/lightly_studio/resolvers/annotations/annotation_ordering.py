"""Shared ordering for annotation queries.

Every query that orders annotations must use the same tiebreaker chain, otherwise the
grid and the detail view's next/prev navigation drift apart.
"""

from __future__ import annotations

from typing import Any, Union

from sqlalchemy.orm import Mapped
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, func

from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoTable

# Expressions the helper sorts itself: model columns come in as `Mapped`, subquery and
# computed columns as `ColumnElement`.
OrderExpression = Union[ColumnElement[Any], Mapped[Any]]


def build_order_by(
    file_path_abs: OrderExpression,
    created_at: OrderExpression,
    annotation_sample_id: OrderExpression,
    leading_order_key: ColumnElement[Any] | None = None,
) -> list[ColumnElement[Any]]:
    """Build the order by clauses for an annotation query.

    Args:
        file_path_abs: Expression for the parent sample's absolute file path.
        created_at: Expression for the annotation's creation time.
        annotation_sample_id: Expression for the annotation's sample ID.
        leading_order_key: Optional expression to order by before the tiebreaker chain,
            e.g. an embedding distance or a metric value. Passed through unchanged, so it
            must already carry its sort direction and null placement, e.g.
            `nullslast(col(...).desc())`.

    Returns:
        Order by clauses: the leading order key if given, then ascending file path,
        creation time and annotation sample ID.
    """
    sort_keys = build_sort_keys(
        file_path_abs=file_path_abs,
        created_at=created_at,
        annotation_sample_id=annotation_sample_id,
    )
    return [
        *([leading_order_key] if leading_order_key is not None else []),
        *(column.asc() if ascending else column.desc() for column, ascending in sort_keys),
    ]


def build_sort_keys(
    file_path_abs: OrderExpression,
    created_at: OrderExpression,
    annotation_sample_id: OrderExpression,
) -> list[tuple[OrderExpression, bool]]:
    """Build the tiebreaker chain as (column, ascending) pairs.

    This is the source of truth `build_order_by` derives its clauses from. Callers that
    need the columns themselves — a keyset seek compares against them rather than sorting
    by them — use this directly.

    Args:
        file_path_abs: Expression for the parent sample's absolute file path.
        created_at: Expression for the annotation's creation time.
        annotation_sample_id: Expression for the annotation's sample ID.

    Returns:
        The parent file path, the creation time and the annotation sample ID, all
        ascending. The sample ID makes the ordering total.
    """
    return [
        (file_path_abs, True),
        (created_at, True),
        (annotation_sample_id, True),
    ]


def file_path_abs_expression(sample_type: SampleType) -> OrderExpression:
    """Get the parent file path expression for a query joining only the given sample type.

    Args:
        sample_type: Sample type of the annotations' parent samples.

    Returns:
        Expression for the parent sample's absolute file path.

    Raises:
        NotImplementedError: If the sample type has no parent file path.
    """
    if sample_type == SampleType.IMAGE:
        return col(ImageTable.file_path_abs)

    if sample_type in (SampleType.VIDEO_FRAME, SampleType.VIDEO):
        return col(VideoTable.file_path_abs)

    raise NotImplementedError(f"Unsupported sample type: {sample_type}")


def coalesced_file_path_abs_expression() -> OrderExpression:
    """Get the parent file path expression for a query joining images and videos alike.

    Returns:
        Expression for the parent sample's absolute file path, empty string if the parent
        is neither an image nor a video frame.
    """
    return func.coalesce(
        col(ImageTable.file_path_abs),
        col(VideoTable.file_path_abs),
        "",
    )
