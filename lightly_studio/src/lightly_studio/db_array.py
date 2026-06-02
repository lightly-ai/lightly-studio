"""Dialect-aware ``in_array`` membership test for UUID columns.

Compiles to ``column = ANY(:array)`` (one bound array parameter) on PostgreSQL to dodge the
65,535 expanding-IN bind cap, and to expanding ``IN`` on DuckDB. Callers must guard against
empty ``values`` (``= ANY(ARRAY[])`` errors on PostgreSQL).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Uuid, any_, bindparam
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.elements import ColumnElement


class in_array(ColumnElement[bool]):  # noqa: N801
    """Membership test over a UUID column, compiled per dialect.

    Use like ``column.in_(values)`` inside ``.where(...)``. On PostgreSQL it binds
    ``values`` as a single ``UUID[]`` array parameter (``column = ANY(:array)``),
    avoiding the 65,535 expanding-IN parameter cap; on DuckDB it falls back to an
    ordinary expanding IN. Callers must ensure ``values`` is non-empty.
    """

    # Holds a raw Python list, which is not safely cache-keyable (cf. db_json.json_extract).
    inherit_cache = False
    type = Boolean()

    def __init__(self, column: Mapped[Any], values: Sequence[UUID]) -> None:
        """Initialize with the UUID column (use ``col(...)``) and non-empty UUID values."""
        self.column = column
        self.values = list(values)


@compiles(in_array)
def _compile_in_array_unsupported(element: in_array, compiler: SQLCompiler, **kw: Any) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(in_array, "duckdb")
def _compile_in_array_duckdb(element: in_array, compiler: SQLCompiler, **kw: Any) -> str:
    """DuckDB: ordinary expanding ``column IN (...)`` (no low bind-parameter cap)."""
    return compiler.process(element.column.in_(element.values), **kw)


@compiles(in_array, "postgresql")
def _compile_in_array_postgresql(element: in_array, compiler: SQLCompiler, **kw: Any) -> str:
    """PostgreSQL: ``column = ANY(:array)`` with a single bound ``UUID[]`` parameter."""
    array_param = bindparam(
        "in_array",
        value=element.values,
        type_=postgresql.ARRAY(Uuid()),
        unique=True,
        expanding=False,
    )
    return compiler.process(element.column == any_(array_param), **kw)
