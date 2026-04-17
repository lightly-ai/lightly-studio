"""Lark Interpreter: parse tree → MatchExpression (skipping intermediate AST)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any, cast

from lark import Token, Tree
from lark.visitors import Interpreter
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


def _decode_string(token: Token) -> str:
    return str(json.loads(str(token)))


def _decode_number(token: Token) -> float | int:
    s = str(token)
    return float(s) if "." in s else int(s)


def _decode_bool(token: Token) -> bool:
    return str(token).lower() == "true"


def _decode_lower(token: Token) -> str:
    return str(token).lower()


_TOKEN_DECODERS: dict[str, Callable[[Token], Any]] = {
    "STRING": _decode_string,
    "SIGNED_NUMBER": _decode_number,
    "BOOL": _decode_bool,
    "CMP_OP": _decode_lower,
}


def _decode_token(value: Any) -> Any:
    """Decode a Lark Token into a Python value.

    Interpreter.visit_children passes terminals through as raw Token objects,
    unlike Transformer which auto-applies terminal handlers. This function
    handles the conversion that the old terminal methods used to do.
    """
    if not isinstance(value, Token):
        return value
    decoder = _TOKEN_DECODERS.get(value.type)
    return decoder(value) if decoder else str(value)


class QueryInterpreter(Interpreter):  # type: ignore[type-arg]
    """Interprets a Lark parse tree into MatchExpression objects directly.

    Operates top-down, which allows context switching for ``has_annotation``:
    the inner subtree is visited with ``context="annotation"`` instead of
    ``"sample"``.
    """

    def __init__(self, registry: FieldRegistry, context: str = "sample") -> None:
        """Initialise the interpreter.

        Args:
            registry: The field registry for resolving field references.
            context: Query context — ``"sample"`` (default) or ``"annotation"``.
        """
        self._registry = registry
        self._context = context

    def or_expr(self, tree: Tree[Any]) -> MatchExpression:
        """Build an OR expression from two or more children."""
        children: list[MatchExpression] = self.visit_children(tree)
        return OR(*children)

    def and_expr(self, tree: Tree[Any]) -> MatchExpression:
        """Build an AND expression from two or more children."""
        children: list[MatchExpression] = self.visit_children(tree)
        return AND(*children)

    def not_expr(self, tree: Tree[Any]) -> MatchExpression:
        """Build a NOT expression wrapping its single child."""
        children: list[MatchExpression] = self.visit_children(tree)
        return NOT(children[0])

    def comparison(self, tree: Tree[Any]) -> MatchExpression:
        """Build a MatchExpression from field, operator, and value."""
        children = [_decode_token(c) for c in self.visit_children(tree)]
        field_ref: list[str] = children[0]
        operator: str = children[1]
        value = children[2]
        return self._build_comparison(field_ref, operator, value)

    def has_tag(self, tree: Tree[Any]) -> MatchExpression:
        """Build a tag membership check."""
        children = [_decode_token(c) for c in self.visit_children(tree)]
        tag_name: str = children[0]
        return TagsAccessor().contains(tag_name)

    def has_annotation(self, tree: Tree[Any]) -> MatchExpression:
        """Build an EXISTS-style IN subquery for annotation matching.

        Creates a new interpreter with ``context="annotation"`` to visit the
        inner subtree, then wraps the result in a correlated subquery.
        """
        inner_interpreter = QueryInterpreter(self._registry, context="annotation")
        inner_expr: MatchExpression = inner_interpreter.visit(tree.children[0])
        return self._build_has_annotation(inner_expr)

    def field_ref(self, tree: Tree[Any]) -> list[str]:
        """Build a field reference from dot-separated name parts."""
        return [str(c) for c in tree.children]

    def list_value(self, tree: Tree[Any]) -> list[Any]:
        """Collect bracketed list values into a Python list."""
        return [_decode_token(c) for c in self.visit_children(tree)]

    # --- Private compilation helpers ---

    def _build_comparison(
        self,
        field_ref: list[str],
        op: str,
        value: Any,
    ) -> MatchExpression:
        """Dispatch a comparison to the appropriate field expression builder."""
        field_info = self._registry.resolve(field_ref, self._context)
        field = field_info.field

        if isinstance(field, OrdinalField):
            if op == "in":
                col_expr = field.get_sqlmodel_field()

                def _in_ordinal() -> ColumnElement[bool]:
                    return col_expr.in_(cast(Iterable[Any], value))

                return _CallableExpression(_in_ordinal)
            ordinal_op: OrdinalOperator = op  # type: ignore[assignment]
            return OrdinalFieldExpression(field=field, operator=ordinal_op, value=value)

        if isinstance(field, ComparableField):
            return self._build_comparable(field, op, value)

        raise ValueError(f"Unsupported field kind in {field_info!r}")

    @staticmethod
    def _build_comparable(
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

    @staticmethod
    def _build_has_annotation(inner_expr: MatchExpression) -> MatchExpression:
        """Compile has_annotation(...) as an EXISTS-style IN subquery.

        Selects ``parent_sample_id`` rows from ``annotation_base`` joined with
        ``annotation_label`` that satisfy the inner expression, then checks that
        the outer sample's ``sample_id`` is in that set.
        """
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
