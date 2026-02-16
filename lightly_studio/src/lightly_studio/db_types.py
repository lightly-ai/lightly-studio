"""Dialect-aware database types and functions.

Provides VectorType and cosine_distance that work across both DuckDB and PostgreSQL
(with pgvector) backends.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ARRAY, Float
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import TypeDecorator, TypeEngine


class VectorType(TypeDecorator[list[float]]):
    """A dialect-aware vector column type.

    Returns pgvector's VECTOR() for PostgreSQL and ARRAY(Float) for DuckDB.
    """

    impl = ARRAY(Float)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Return the dialect-specific type: pgvector VECTOR or ARRAY(Float)."""
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector())
        return dialect.type_descriptor(ARRAY(Float))


class cosine_distance(GenericFunction[float]):  # noqa: N801
    """Cosine distance function that compiles to dialect-specific SQL.

    Uses the <=> operator on both DuckDB and PostgreSQL (pgvector).
    PostgreSQL requires an explicit ::vector cast on the right operand.
    """

    type = Float()
    inherit_cache = True


@compiles(cosine_distance)
def _compile_cosine_distance_default(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """Default compilation (DuckDB): uses <=> without cast."""
    left, right = list(element.clauses)
    return f"({compiler.process(left, **kw)} <=> {compiler.process(right, **kw)})"


@compiles(cosine_distance, "postgresql")
def _compile_cosine_distance_postgresql(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: uses <=> with ::vector cast on the right operand."""
    left, right = list(element.clauses)
    return f"({compiler.process(left, **kw)} <=> {compiler.process(right, **kw)}::vector)"
