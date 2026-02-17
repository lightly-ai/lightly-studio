"""Dialect-aware vector types and functions.

Provides VectorType and cosine_distance that work across both DuckDB and PostgreSQL
(with pgvector) backends.
"""

from __future__ import annotations

from typing import Any, List

from sqlalchemy import ARRAY, Float
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import TypeDecorator, TypeEngine


class VectorType(TypeDecorator[List[float]]):
    """A dialect-aware vector column type.

    Returns pgvector's VECTOR() for PostgreSQL and ARRAY(Float) for DuckDB.
    """

    impl = ARRAY(Float)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Return the dialect-specific type for the vector column.

        Returns pgvector VECTOR for PostgreSQL and ARRAY(Float) for DuckDB.
        Raises NotImplementedError for unsupported dialects.
        """
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector())
        if dialect.name == "duckdb":
            return dialect.type_descriptor(ARRAY(Float))
        raise NotImplementedError(
            f"Unsupported dialect: {dialect.name}. Only 'postgresql' and 'duckdb' are supported."
        )


class cosine_distance(GenericFunction[float]):  # noqa: N801
    """Cosine distance function that compiles to dialect-specific SQL.

    Uses the <=> operator on both DuckDB and PostgreSQL (pgvector).
    PostgreSQL requires explicit ::vector casts on both operands.
    """

    type = Float()
    inherit_cache = True


@compiles(cosine_distance)
def _compile_cosine_distance_unsupported(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(cosine_distance, "duckdb")
def _compile_cosine_distance_duckdb(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """DuckDB compilation: uses <=> without cast."""
    left, right = list(element.clauses)
    return f"({compiler.process(left, **kw)} <=> {compiler.process(right, **kw)})"


@compiles(cosine_distance, "postgresql")
def _compile_cosine_distance_postgresql(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: uses <=> with ::vector cast on both operands."""
    left, right = list(element.clauses)
    return f"({compiler.process(left, **kw)}::vector <=> {compiler.process(right, **kw)}::vector)"
