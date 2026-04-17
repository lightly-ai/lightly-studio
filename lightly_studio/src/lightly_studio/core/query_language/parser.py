"""Parse query text into a MatchExpression using the Lark grammar."""

from __future__ import annotations

from pathlib import Path

from lark import Lark

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.query_language.field_registry import FieldRegistry
from lightly_studio.core.query_language.transformer import QueryInterpreter

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"

# Build the LALR parser once at import time. The contextual lexer (default for
# LALR in Lark) handles keyword/identifier disambiguation automatically.
_PARSER = Lark(_GRAMMAR_PATH.read_text(), parser="lalr", start="query")


def parse_query(text: str, registry: FieldRegistry) -> MatchExpression:
    """Parse a query string into a MatchExpression.

    Args:
        text: The query text, e.g. ``'width > 100 and has_tag("train")'``.
        registry: The field registry for resolving field references.

    Returns:
        A ``MatchExpression`` whose ``.get()`` yields a SQLAlchemy bool expression.

    Raises:
        lark.exceptions.LarkError: If ``text`` is syntactically invalid.
        ValueError: On unknown fields or operators.
    """
    tree = _PARSER.parse(text)
    return QueryInterpreter(registry).visit(tree)  # type: ignore[no-any-return]
