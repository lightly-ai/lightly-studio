"""Sorting models and translation utilities."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.models.sort_direction import SortDirection


class SortFieldSource(str, Enum):
    """Source of the field to sort by."""

    image = "image"
    video = "video"
    metadata = "metadata"
    evaluation_metric = "evaluation_metric"
    similarity = "similarity"


class SortFieldExprBase(BaseModel):
    """Fields shared by every single-field sorting expression.

    Subclasses narrow ``source`` to the sources their endpoint can reach. A sample
    table only appears in the FROM clause of queries over that sample type, so a
    field from the wrong source would be cross-joined instead of rejected.

    Attributes:
        source: The source of the field (e.g., "image", "video" or "metadata").
        field_name: The field to sort by.
        direction: The sort direction, either ascending or descending.
    """

    source: SortFieldSource
    field_name: str
    direction: SortDirection


class ImageSortFieldExpr(SortFieldExprBase):
    """A sorting expression for a single field of an image."""

    source: Literal[SortFieldSource.image, SortFieldSource.metadata]


class VideoSortFieldExpr(SortFieldExprBase):
    """A sorting expression for a single field of a video.

    Evaluation metrics are image-only, so they have no counterpart here.
    """

    source: Literal[SortFieldSource.video, SortFieldSource.metadata]


class EvaluationMetricSortExpr(BaseModel):
    """A sorting expression for an evaluation metric field.

    Attributes:
        source: Always ``"evaluation_metric"`` (discriminator for the union type).
        evaluation_run_name: The name of the evaluation run to sort by.
        metric_name: The metric name to sort by.
        direction: The sort direction, either ascending or descending.
    """

    source: Literal[SortFieldSource.evaluation_metric] = SortFieldSource.evaluation_metric
    evaluation_run_name: str
    metric_name: str
    direction: SortDirection


class SimilaritySortExpr(BaseModel):
    """A sorting expression for the similarity to the text search.

    Applies only while a text search is active and is ignored otherwise.

    Attributes:
        source: Always ``"similarity"`` (discriminator for the union type).
        direction: The sort direction. Descending shows the most similar samples first.
    """

    source: Literal[SortFieldSource.similarity] = SortFieldSource.similarity
    direction: SortDirection


ImageSortExpr = Annotated[
    Union[ImageSortFieldExpr, EvaluationMetricSortExpr, SimilaritySortExpr],
    Field(discriminator="source"),
]


VideoSortExpr = Annotated[
    Union[VideoSortFieldExpr, SimilaritySortExpr],
    Field(discriminator="source"),
]


# Image and video field expressions both allow ``source="metadata"``, so a
# discriminated union on ``source`` cannot build. Match left to right instead: a
# metadata expression resolves to ``ImageSortFieldExpr``, which is harmless since
# both translate through the same ``(source, field_name)`` key.
# TODO(gabriel, 08/2026): Replace this left-to-right union with a source-discriminated one;
# tracked in LIG-10605. Safe only while ImageSortFieldExpr and VideoSortFieldExpr stay
# structurally identical, guarded by
# tests/models/test_sort.py::test_image_and_video_sort_field_exprs_stay_structurally_identical.
AdjacentSortExpr = Annotated[
    Union[ImageSortFieldExpr, VideoSortFieldExpr, EvaluationMetricSortExpr, SimilaritySortExpr],
    Field(union_mode="left_to_right"),
]


def get_similarity_direction(sort_by: Sequence[AdjacentSortExpr] | None) -> SortDirection:
    """Get the similarity sort direction from the sort expressions.

    Args:
        sort_by: The sort expressions from the API request, or None.

    Returns:
        The direction of the first similarity expression, descending if there is none.
    """
    for expr in sort_by or []:
        if isinstance(expr, SimilaritySortExpr):
            return expr.direction
    return SortDirection.desc


def sort_exprs_to_order_by(
    sort_by: Sequence[AdjacentSortExpr] | None,
) -> list[OrderByExpression] | None:
    """Translate the field sort expressions to OrderByExpressions.

    Similarity expressions are skipped. They need the text embedding, so the resolvers
    apply them, see ``get_similarity_direction``.

    Args:
        sort_by: The sort expressions from the API request, or None.

    Returns:
        The translated expressions, or None when no field sort was requested.
    """
    order_by = [
        adjacent_sort_expr_to_order_by(expr)
        for expr in sort_by or []
        if not isinstance(expr, SimilaritySortExpr)
    ]
    return order_by or None


def sort_field_expr_to_order_by(expr: SortFieldExprBase) -> OrderByExpression:
    """Translate a single-field sort expression to an OrderByExpression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    return query_translation.sort_to_order_by(
        key=(expr.source, expr.field_name),
        direction=expr.direction,
    )


def image_sort_expr_to_order_by(
    expr: ImageSortFieldExpr | EvaluationMetricSortExpr,
) -> OrderByExpression:
    """Translate an image, metadata, or evaluation metric sort to an OrderByExpression.

    Args:
        expr: The sort expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    return adjacent_sort_expr_to_order_by(expr)


def adjacent_sort_expr_to_order_by(
    expr: ImageSortFieldExpr | VideoSortFieldExpr | EvaluationMetricSortExpr,
) -> OrderByExpression:
    """Translate an adjacency sort expression to an OrderByExpression.

    Handles image, video, metadata, and evaluation-metric expressions, so the
    shared adjacent-samples request can carry the sort of either grid.

    Args:
        expr: The sort expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    if isinstance(expr, EvaluationMetricSortExpr):
        return query_translation.evaluation_metric_sort_to_order_by(
            evaluation_run_name=expr.evaluation_run_name,
            metric_name=expr.metric_name,
            direction=expr.direction,
        )
    return sort_field_expr_to_order_by(expr)
