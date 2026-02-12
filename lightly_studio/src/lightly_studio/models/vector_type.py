"""Dialect-aware vector column type and cosine distance function.

Provides a ``VectorType`` that maps to pgvector's ``VECTOR`` on PostgreSQL and
``ARRAY(Float)`` on DuckDB, and a ``cosine_distance`` generic function compiled
to the ``<=>`` operator on both backends.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ARRAY, Float, types
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import GenericFunction


class VectorType(types.TypeDecorator[list[float]]):
    """A dialect-aware vector column type.

    Stores embedding vectors as pgvector ``VECTOR`` on PostgreSQL and as
    ``ARRAY(Float)`` on DuckDB.
    """

    impl = ARRAY(Float)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Return the dialect-specific column type."""
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import VECTOR

            return dialect.type_descriptor(VECTOR())
        return dialect.type_descriptor(ARRAY(Float))


class cosine_distance(GenericFunction):  # noqa: N801
    """Cosine distance function compiled to the ``<=>`` operator.

    Supported by both pgvector (PostgreSQL) and DuckDB (v1.2+ aliases
    ``list_cosine_distance`` to ``<=>``).
    """

    type = Float()
    inherit_cache = True


@compiles(cosine_distance)
def _compile_cosine_distance(element: Any, compiler: Any, **kw: Any) -> str:
    """Compile ``cosine_distance`` to the ``<=>`` operator."""
    args = list(element.clauses)
    left = compiler.process(args[0], **kw)
    right = compiler.process(args[1], **kw)
    return f"({left} <=> {right}::vector)" # this will break for DuckDB - has to be properly handled in the actual PR
