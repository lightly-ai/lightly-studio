"""Dialect-aware JSON extraction functions.

Provides ``json_extract`` and ``json_literal`` that compile to the correct SQL
syntax for DuckDB and PostgreSQL.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Text, literal
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import TypeDecorator


def json_literal(value: Any) -> BindParameter[Any]:
    """Create a dialect-aware literal for JSON comparisons.

    For string values the returned bind parameter uses ``_JsonStringType``
    which JSON-encodes the value on DuckDB (matching ``json_extract`` output)
    while passing it through unchanged on PostgreSQL (where ``->>`` already
    returns plain text).

    For non-string values a regular ``literal()`` is returned.
    """
    if isinstance(value, str):
        return literal(value, type_=_JsonStringType())
    return literal(value)


class json_extract(GenericFunction[Any]):  # noqa: N801
    """Extract a value from a JSON column by field path.

    Compiles to dialect-specific SQL:
    - DuckDB:      ``json_extract(col, '$.field')``
    - PostgreSQL:  ``col->>'field'``

    When *cast_to_float* is ``True``:
    - DuckDB:      ``CAST(json_extract(col, '$.field') AS FLOAT)``
    - PostgreSQL:  ``(col->>'field')::float``

    ``field`` supports dot-separated paths (``a.b.c``) and array indices (``a.list[0]``).
    """

    # Field path and cast flag vary per instance, so caching is unsafe.
    inherit_cache = False

    def __init__(
        self,
        column: Any,
        field: str,
        *,
        cast_to_float: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize with a column, field path, and optional float cast.

        Args:
            column: The JSON column expression (e.g. ``SampleMetadataTable.data``).
            field: Dot-separated path into the JSON object.
            cast_to_float: If True, cast the extracted value to float.
            **kwargs: Additional keyword arguments forwarded to GenericFunction.
        """
        self.field = field
        self.cast_to_float = cast_to_float
        super().__init__(column, **kwargs)


@compiles(json_extract)
def _compile_json_extract_unsupported(
    element: json_extract, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(json_extract, "duckdb")
def _compile_json_extract_duckdb(element: json_extract, compiler: SQLCompiler, **kw: Any) -> str:
    """DuckDB compilation: ``json_extract(col, '$.field')``."""
    # element.clauses contains a single item: the column passed to __init__.
    col = next(iter(element.clauses))
    json_path = "$." + element.field
    expr = f"json_extract({compiler.process(col, **kw)}, '{json_path}')"
    if element.cast_to_float:
        expr = f"CAST({expr} AS FLOAT)"
    return expr


@compiles(json_extract, "postgresql")
def _compile_json_extract_postgresql(
    element: json_extract, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: ``col->>'field'`` with optional ``::float`` cast."""
    # element.clauses contains a single item: the column passed to __init__.
    col = next(iter(element.clauses))
    col_sql = compiler.process(col, **kw)
    return _build_pg_json_accessor(
        column=col_sql, field=element.field, cast_to_float=element.cast_to_float
    )


class _JsonStringType(TypeDecorator[str]):
    r"""Bind-parameter type that JSON-encodes strings on DuckDB only.

    DuckDB's ``json_extract`` returns JSON-encoded values, so comparison
    values must also be JSON-encoded to match.  PostgreSQL's ``->>``
    returns plain text, so strings pass through unchanged.

    Example for ``{"key": "value"}``:

    - DuckDB:      ``json_extract(data, '$.key')`` returns ``'"value"'``
                    -> bind param must be ``'"paris"'`` (via ``json.dumps``)
    - PostgreSQL:  ``data->>'key'`` returns ``'value'``
                    -> bind param must be ``'value'`` (raw string)
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        """Encode string values as JSON for DuckDB, pass through for PostgreSQL."""
        if value is None:
            return None
        if dialect.name == "duckdb":
            return json.dumps(value)
        return value


def _build_pg_json_accessor(column: str, field: str, *, cast_to_float: bool = False) -> str:
    """Build a PostgreSQL JSON accessor expression from a dot-separated field path.

    Converts paths like ``dict.key`` into ``col->'dict'->>'key'`` operator chains.

    Args:
        column: Already-compiled column SQL string.
        field: Dot-separated path into the JSON object.
        cast_to_float: If True, wrap the expression in ``(...)::float``.

    Returns:
        A raw SQL expression string.
    """
    # Split on '.' but keep bracket notation (e.g. "nested_list[0]" -> "nested_list", "[0]")
    parts = field.replace("[", ".[").split(".")

    accessors: list[str] = []
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        op = "->>" if is_last else "->"
        if part.startswith("[") and part.endswith("]"):
            # Array index access: ->>0 or ->0 (unquoted integer)
            index = part[1:-1]
            accessors.append(f"{op}{index}")
        else:
            accessors.append(f"{op}'{part}'")

    expr = column + "".join(accessors)
    if cast_to_float:
        expr = f"({expr})::float"
    return expr
