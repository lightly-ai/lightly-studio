"""Lark Transformer: parse tree → query language AST nodes."""

from __future__ import annotations

import json
from typing import Any

from lark import Token, Transformer

from lightly_studio.core.query_language.ast_nodes import (
    AndNode,
    ComparisonNode,
    HasAnnotationNode,
    HasTagNode,
    NotNode,
    OrNode,
    QueryNode,
)


class QueryTransformer(Transformer):  # type: ignore[type-arg]
    """Maps Lark tree nodes to strongly-typed AST nodes.

    Rules marked with ``?`` in the grammar are inlined by Lark when they have a
    single child, so OR/AND handlers are only called for multi-child cases.
    """

    def or_expr(self, children: list[QueryNode]) -> OrNode:
        """Create an OR node from two or more children."""
        return OrNode(children=children)

    def and_expr(self, children: list[QueryNode]) -> AndNode:
        """Create an AND node from two or more children."""
        return AndNode(children=children)

    def not_expr(self, children: list[QueryNode]) -> NotNode:
        """Create a NOT node wrapping its single child."""
        return NotNode(child=children[0])

    def comparison(self, children: list[Any]) -> ComparisonNode:
        """Create a comparison node from field, operator, and value."""
        field_ref, operator, value = children
        return ComparisonNode(field=field_ref, operator=str(operator), value=value)

    def has_tag(self, children: list[Any]) -> HasTagNode:
        """Create a has_tag node; children[0] is already an unquoted Python string."""
        return HasTagNode(tag_name=str(children[0]))

    def has_annotation(self, children: list[QueryNode]) -> HasAnnotationNode:
        """Create a has_annotation node with the inner query as its child."""
        return HasAnnotationNode(inner=children[0])

    def field_ref(self, children: list[Any]) -> list[str]:
        """Build a field reference from dot-separated name parts."""
        return [str(c) for c in children]

    def list_value(self, children: list[Any]) -> list[Any]:
        """Collect bracketed list values into a Python list."""
        return list(children)

    # --- Terminal transformers ---

    def STRING(self, token: Token) -> str:  # noqa: N802
        """Decode ESCAPED_STRING (e.g. ``"hello"`` → ``hello``)."""
        return str(json.loads(str(token)))

    def SIGNED_NUMBER(self, token: Token) -> float | int:  # noqa: N802
        """Parse number as int when possible, float otherwise."""
        s = str(token)
        return float(s) if "." in s else int(s)

    def BOOL(self, token: Token) -> bool:  # noqa: N802
        """Parse a boolean literal to a Python bool."""
        return str(token).lower() == "true"

    def CMP_OP(self, token: Token) -> str:  # noqa: N802
        """Normalize comparison operator to lowercase."""
        return str(token).lower()
