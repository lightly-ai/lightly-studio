"""Convert dataset-query expressions to the query format that the transport sends.

Only image sample fields and tags are supported. Other expressions raise
`UnsupportedQueryError`, and the caller uses the SQL path.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field import Field
from lightly_studio.core.dataset_query.field_expression import (
    ComparableFieldExpression,
    OrdinalFieldExpression,
)
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.core.dataset_query.tags_expression import TagsContainsExpression
from lightly_studio.models.query_expr import (
    AndExpr,
    DatetimeExpr,
    EqualityComparisonOperator,
    FieldRef,
    IntegerExpr,
    MatchExpr,
    NotExpr,
    OrdinalComparisonOperator,
    OrExpr,
    QueryExpr,
    StringExpr,
    TagsContainsExpr,
)
from lightly_studio.models.sample_query import SortKey
from lightly_studio.models.sort_direction import SortDirection

_IMAGE_FIELDS: list[tuple[Field, str]] = [
    (ImageSampleField.file_name, "file_name"),
    (ImageSampleField.file_path_abs, "file_path_abs"),
    (ImageSampleField.width, "width"),
    (ImageSampleField.height, "height"),
    (ImageSampleField.created_at, "created_at"),
]


class UnsupportedQueryError(NotImplementedError):
    """The transport cannot send this query yet."""


def to_query_expr(match_expression: MatchExpression) -> QueryExpr:
    """Convert a match expression to a `QueryExpr`.

    Raises:
        UnsupportedQueryError: If the expression uses a field that is not supported.
    """
    try:
        return QueryExpr(match_expr=_to_match_expr(expression=match_expression))
    except ValidationError as error:
        raise UnsupportedQueryError(f"The filter is not supported: {error}") from error


def to_sort_keys(order_by: Sequence[OrderByExpression]) -> list[SortKey]:
    """Convert order-by expressions to sort keys.

    Raises:
        UnsupportedQueryError: If a sort is not on an image sample field.
    """
    keys = []
    for expression in order_by:
        if not isinstance(expression, OrderByField):
            raise UnsupportedQueryError(f"The sort {type(expression).__name__} is not supported.")
        direction = SortDirection.asc if expression.ascending else SortDirection.desc
        keys.append(SortKey(field=_field_ref(field=expression.field), direction=direction))
    return keys


def _to_match_expr(expression: MatchExpression) -> MatchExpr:
    if isinstance(expression, AND):
        return AndExpr(children=[_to_match_expr(expression=term) for term in expression.terms])
    if isinstance(expression, OR):
        return OrExpr(children=[_to_match_expr(expression=term) for term in expression.terms])
    if isinstance(expression, NOT):
        return NotExpr(child=_to_match_expr(expression=expression.term))
    if isinstance(expression, TagsContainsExpression):
        tags = FieldRef(table="image", name="tags")
        return TagsContainsExpr(field=tags, tag_name=expression.tag_name)
    if isinstance(expression, (ComparableFieldExpression, OrdinalFieldExpression)):
        return _field_to_match_expr(expression=expression)
    raise UnsupportedQueryError(f"The filter {type(expression).__name__} is not supported.")


def _field_to_match_expr(
    expression: ComparableFieldExpression[Any] | OrdinalFieldExpression[Any],
) -> MatchExpr:
    field = _field_ref(field=expression.field)
    if isinstance(expression, ComparableFieldExpression):
        operator = EqualityComparisonOperator(expression.operator)
        return StringExpr(field=field, operator=operator, value=expression.value)
    ordinal_operator = OrdinalComparisonOperator(expression.operator)
    if field.name == "created_at":
        return DatetimeExpr(field=field, operator=ordinal_operator, value=expression.value)
    return IntegerExpr(field=field, operator=ordinal_operator, value=expression.value)


def _field_ref(field: Field) -> FieldRef:
    # Fields overload `==`, so the lookup compares identity.
    for image_field, name in _IMAGE_FIELDS:
        if field is image_field:
            return FieldRef(table="image", name=name)
    raise UnsupportedQueryError(f"The field {type(field).__name__} is not supported.")
