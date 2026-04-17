"""Parse query text into an AST using the Lark grammar."""

from __future__ import annotations

from pathlib import Path

from lark import Lark

from lightly_studio.core.query_language.ast_nodes import QueryNode
from lightly_studio.core.query_language.transformer import QueryTransformer

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"

# Build the LALR parser once at import time. The contextual lexer (default for
# LALR in Lark) handles keyword/identifier disambiguation automatically.
_PARSER = Lark(_GRAMMAR_PATH.read_text(), parser="lalr", start="query")


def parse_to_ast(text: str) -> QueryNode:
    """Parse a query string into an AST node.

    Args:
        text: The query text, e.g. ``'width > 100 and has_tag("train")'``.

    Returns:
        The root ``QueryNode`` of the parsed expression.

    Raises:
        lark.exceptions.LarkError: If ``text`` is syntactically invalid.
    """
    tree = _PARSER.parse(text)
    return QueryTransformer().transform(tree)  # type: ignore[no-any-return]
