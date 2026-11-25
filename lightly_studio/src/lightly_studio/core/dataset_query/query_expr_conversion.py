"""Convert dataset-query expressions to the query format that the transport sends.

Only sample fields, tags, and metadata are supported. Other expressions raise
`UnsupportedQueryError`, and the caller uses the SQL path.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field import Field
from lightly_studio.core.dataset_query.field_expression import (
    ComparableFieldExpression,
    OrdinalFieldExpression,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.metadata_expression import MetadataComparisonExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.core.dataset_query.query_translation import FieldExpr
from lightly_studio.core.dataset_query.tags_expression import TagsContainsExpression
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    AndExpr,
    FieldRef,
    MatchExpr,
    MetadataComparisonExpr,
    NotExpr,
    OrdinalComparisonOperator,
    OrExpr,
    QueryExpr,
    TagsContainsExpr,
)
from lightly_studio.models.sample_query import SortKey
from lightly_studio.models.sort_direction import SortDirection


class UnsupportedQueryError(NotImplementedError):
    """The transport cannot send this query yet."""


def to_query_expr(match_expression: MatchExpression, sample_type: SampleType) -> QueryExpr:
    """Convert a match expression on samples of the sample type to a `QueryExpr`.

    Raises:
        UnsupportedQueryError: If the expression uses a field that is not supported.
    """
    try:
        match_expr = _to_match_expr(expression=match_expression, scope=sample_type.value)
        return QueryExpr(match_expr=match_expr)
    except ValidationError as error:
        raise UnsupportedQueryError(f"The filter is not supported: {error}") from error


def to_sort_keys(order_by: Sequence[OrderByExpression], sample_type: SampleType) -> list[SortKey]:
    """Convert order-by expressions on samples of the sample type to sort keys.

    Raises:
        UnsupportedQueryError: If a sort is not on a sample field.
    """
    keys = []
    for expression in order_by:
        if not isinstance(expression, OrderByField):
            raise UnsupportedQueryError(f"The sort {type(expression).__name__} is not supported.")
        direction = SortDirection.asc if expression.ascending else SortDirection.desc
        field_ref, _ = _lookup_field(field=expression.field, scope=sample_type.value)
        keys.append(SortKey(field=field_ref, direction=direction))
    return keys


def _to_match_expr(expression: MatchExpression, scope: str) -> MatchExpr:
    if isinstance(expression, AND):
        return AndExpr(
            children=[_to_match_expr(expression=term, scope=scope) for term in expression.terms]
        )
    if isinstance(expression, OR):
        return OrExpr(
            children=[_to_match_expr(expression=term, scope=scope) for term in expression.terms]
        )
    if isinstance(expression, NOT):
        return NotExpr(child=_to_match_expr(expression=expression.term, scope=scope))
    if isinstance(expression, TagsContainsExpression):
        if not query_translation.has_tags(table=scope):
            raise UnsupportedQueryError(f"Tags of {scope} are not supported.")
        tags = FieldRef(table=scope, name="tags")
        return TagsContainsExpr(field=tags, tag_name=expression.tag_name)
    if isinstance(expression, MetadataComparisonExpression):
        operator = OrdinalComparisonOperator(expression.comparison)
        return MetadataComparisonExpr(
            path=expression.path, operator=operator, value=expression.value
        )
    if isinstance(expression, (ComparableFieldExpression, OrdinalFieldExpression)):
        field_ref, expr_type = _lookup_field(field=expression.field, scope=scope)
        return expr_type.model_validate(
            {"field": field_ref, "operator": expression.operator, "value": expression.value}
        )
    raise UnsupportedQueryError(f"The filter {type(expression).__name__} is not supported.")


def _lookup_field(field: Field, scope: str) -> tuple[FieldRef, type[FieldExpr]]:
    fields_by_column = _fields_by_column()
    key = (scope, field.get_sqlmodel_field())
    if key not in fields_by_column:
        raise UnsupportedQueryError(f"The field {type(field).__name__} is not supported.")
    return fields_by_column[key]


@functools.cache
def _fields_by_column() -> dict[tuple[str, Any], tuple[FieldRef, type[FieldExpr]]]:
    """Map (table, column) to the field reference and the expression type of the field."""
    fields_by_column: dict[tuple[str, Any], tuple[FieldRef, type[FieldExpr]]] = {}
    for expr_type, fields in query_translation.field_tables():
        for (table, name), field in fields.items():
            if isinstance(field, Field):
                key = (table, field.get_sqlmodel_field())
                # The first table of a column wins.
                fields_by_column.setdefault(key, (FieldRef(table=table, name=name), expr_type))
    return fields_by_column
