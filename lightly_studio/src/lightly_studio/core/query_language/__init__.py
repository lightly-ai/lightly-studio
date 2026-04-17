"""Query language: text → Lark parse tree → MatchExpression → SQLAlchemy.

Public API::

    from lightly_studio.core.query_language import FieldRegistry, parse_query

    registry = FieldRegistry()
    match_expr = parse_query('width > 100 and has_tag("train")', registry)
    sql_condition = match_expr.get()  # ColumnElement[bool]
"""

from lightly_studio.core.query_language.field_registry import FieldRegistry
from lightly_studio.core.query_language.parser import parse_query

__all__ = ["FieldRegistry", "parse_query"]
