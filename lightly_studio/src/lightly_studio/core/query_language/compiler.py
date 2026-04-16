"""Compiles query AST nodes into MatchExpression objects."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, cast

from sqlalchemy import ColumnElement
from sqlmodel import col, select

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field import ComparableField, OrdinalField
from lightly_studio.core.dataset_query.field_expression import (
    ComparableFieldExpression,
    ComparisonOperator,
    OrdinalFieldExpression,
    OrdinalOperator,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.core.query_language.ast_nodes import (
    AndNode,
    ComparisonNode,
    HasAnnotationNode,
    HasTagNode,
    NotNode,
    OrNode,
    QueryNode,
)
from lightly_studio.core.query_language.field_registry import FieldRegistry
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable


class _CallableExpression(MatchExpression):
    """MatchExpression backed by a zero-argument callable."""

    def __init__(self, fn: Callable[[], ColumnElement[bool]]) -> None:
        """Initialise with a callable that produces a SQLAlchemy bool expression."""
        self._fn = fn

    def get(self) -> ColumnElement[bool]:
        """Return the SQLAlchemy expression from the wrapped callable."""
        return self._fn()


def compile_ast(
    node: QueryNode,
    registry: FieldRegistry,
    context: str = "sample",
) -> MatchExpression:
    """Compile an AST node into a SQLAlchemy-compatible MatchExpression.

    Args:
        node: The AST node to compile.
        registry: The field registry for resolving field references.
        context: Query context — ``"sample"`` (default) or ``"annotation"``.

    Returns:
        A ``MatchExpression`` whose ``.get()`` yields a SQLAlchemy bool expression.
    """
    if isinstance(node, ComparisonNode):
        return _compile_comparison(node, registry, context)
    if isinstance(node, AndNode):
        return AND(*[compile_ast(c, registry, context) for c in node.children])
    if isinstance(node, OrNode):
        return OR(*[compile_ast(c, registry, context) for c in node.children])
    if isinstance(node, NotNode):
        return NOT(compile_ast(node.child, registry, context))
    if isinstance(node, HasTagNode):
        return TagsAccessor().contains(node.tag_name)
    if isinstance(node, HasAnnotationNode):
        return _compile_has_annotation(node, registry)
    raise ValueError(f"Unknown node type: {type(node)!r}")  # pragma: no cover


def _compile_comparison(
    node: ComparisonNode, registry: FieldRegistry, context: str
) -> MatchExpression:
    """Dispatch a ComparisonNode to the appropriate field expression builder."""
    field_info = registry.resolve(node.field, context)
    field = field_info.field
    op = node.operator
    value = node.value

    if isinstance(field, OrdinalField):
        if op == "in":
            col_expr = field.get_sqlmodel_field()

            def _in_ordinal() -> ColumnElement[bool]:
                return col_expr.in_(cast(Iterable[Any], value))

            return _CallableExpression(_in_ordinal)
        ordinal_op: OrdinalOperator = op  # type: ignore[assignment]
        return OrdinalFieldExpression(field=field, operator=ordinal_op, value=value)

    if isinstance(field, ComparableField):
        return _compile_comparable(field, op, value)

    raise ValueError(f"Unsupported field kind in {field_info!r}")


def _compile_comparable(
    field: ComparableField[str],
    op: str,
    value: object,
) -> MatchExpression:
    """Build a MatchExpression for a ComparableField (string-like) field."""
    col_expr = field.get_sqlmodel_field()
    if op == "contains":
        str_value = str(value)

        def _contains() -> ColumnElement[bool]:
            return col_expr.contains(str_value)

        return _CallableExpression(_contains)
    if op == "in":
        iterable_value = cast(Iterable[Any], value)

        def _in() -> ColumnElement[bool]:
            return col_expr.in_(iterable_value)

        return _CallableExpression(_in)
    comparable_op: ComparisonOperator = op  # type: ignore[assignment]
    return ComparableFieldExpression(field=field, operator=comparable_op, value=str(value))


def _compile_has_annotation(node: HasAnnotationNode, registry: FieldRegistry) -> MatchExpression:
    """Compile has_annotation(...) as an EXISTS-style IN subquery.

    Selects ``parent_sample_id`` rows from ``annotation_base`` joined with
    ``annotation_label`` that satisfy the inner expression, then checks that
    the outer sample's ``sample_id`` is in that set.
    """
    inner_expr = compile_ast(node.inner, registry, context="annotation")
    subquery = (
        select(AnnotationBaseTable.parent_sample_id)
        .join(
            AnnotationLabelTable,
            AnnotationBaseTable.annotation_label_id == AnnotationLabelTable.annotation_label_id,  # type: ignore[arg-type]
        )
        .where(inner_expr.get())
        .distinct()
    )
    sample_id_col = col(ImageTable.sample_id)

    def _in_subquery() -> ColumnElement[bool]:
        return sample_id_col.in_(subquery)

    return _CallableExpression(_in_subquery)
