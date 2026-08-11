"""Dialect-aware JSON extraction functions.

Provides ``json_extract`` and ``json_literal`` that compile to the correct SQL
syntax for DuckDB and PostgreSQL.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

import sqlalchemy
from sqlalchemy import Text
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import TypeDecorator

_ARRAY_INDEX_PATTERN = re.compile(r"^\[([0-9]+)\]$")


def json_literal(value: Any) -> BindParameter[Any]:
    """Create a dialect-aware literal for JSON comparisons.

    For string values the returned bind parameter uses ``_JsonStringType``
    which JSON-encodes the value on DuckDB (matching ``json_extract`` output)
    while passing it through unchanged on PostgreSQL (where ``->>`` already
    returns plain text).

    For non-string values a regular ``literal()`` is returned.
    """
    if isinstance(value, str):
        return sqlalchemy.literal(value, type_=_JsonStringType())
    return sqlalchemy.literal(value)


class json_extract(GenericFunction[Any]):  # noqa: N801
    """Extract a value from a JSON column by field path.

    Keys are bound rather than interpolated into SQL, so quotes and other special
    characters in metadata keys cannot alter the statement.

    Compiles to dialect-specific SQL:
    - DuckDB:      ``json_extract(col, :path)`` with a JSON Pointer path
    - PostgreSQL:  ``col->>:key``

    When *cast_to_float* is ``True``:
    - DuckDB:      ``CAST(json_extract(col, :path) AS FLOAT)``
    - PostgreSQL:  ``(col->>:key)::float``

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
    ) -> None:
        """Initialize with a column, field path, and optional float cast.

        Args:
            column: The JSON column expression (e.g. ``SampleMetadataTable.data``).
            field: Dot-separated path into the JSON object.
            cast_to_float: If True, cast the extracted value to float.
        """
        segments = _parse_field_path(field)
        self.cast_to_float = cast_to_float
        # Parameters are built once per instance so that repeated renderings of the same
        # expression (e.g. in SELECT and in GROUP BY) reuse one parameter and stay equal.
        self.duckdb_path = sqlalchemy.literal(_to_json_pointer(segments), type_=Text())
        self.postgres_segments = [
            segment if isinstance(segment, int) else sqlalchemy.literal(segment, type_=Text())
            for segment in segments
        ]
        super().__init__(column)


class json_extract_string(GenericFunction[str]):  # noqa: N801
    """Extract a top-level JSON scalar as plain text.

    The key is bound rather than interpolated into SQL. It is treated literally,
    so dots and quotes in metadata keys do not become path syntax.
    """

    inherit_cache = False
    type = Text()

    def __init__(self, column: Any, field: str) -> None:
        """Initialize with a JSON column and top-level field name."""
        field_parameter = sqlalchemy.literal(field, type_=_JsonTopLevelKeyType())
        super().__init__(column, field_parameter)


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
    """DuckDB compilation: ``json_extract(col, :path)`` with a bound JSON Pointer."""
    # element.clauses contains a single item: the column passed to __init__.
    col = next(iter(element.clauses))
    path = compiler.process(element.duckdb_path, **kw)
    expr = f"json_extract({compiler.process(col, **kw)}, {path})"
    if element.cast_to_float:
        expr = f"CAST({expr} AS FLOAT)"
    return expr


@compiles(json_extract, "postgresql")
def _compile_json_extract_postgresql(
    element: json_extract, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: ``col->>:key`` with optional ``::float`` cast."""
    # element.clauses contains a single item: the column passed to __init__.
    col = next(iter(element.clauses))
    col_sql = compiler.process(col, **kw)
    return _build_pg_json_accessor(
        column=col_sql,
        segments=element.postgres_segments,
        compiler=compiler,
        cast_to_float=element.cast_to_float,
        **kw,
    )


@compiles(json_extract_string)
def _compile_json_extract_string_unsupported(
    element: json_extract_string, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(json_extract_string, "duckdb")
def _compile_json_extract_string_duckdb(
    element: json_extract_string, compiler: SQLCompiler, **kw: Any
) -> str:
    """Extract a JSON scalar as plain text on DuckDB."""
    column, field = element.clauses
    return f"json_extract_string({compiler.process(column, **kw)}, {compiler.process(field, **kw)})"


@compiles(json_extract_string, "postgresql")
def _compile_json_extract_string_postgresql(
    element: json_extract_string, compiler: SQLCompiler, **kw: Any
) -> str:
    """Extract a JSON scalar as plain text on PostgreSQL."""
    column, field = element.clauses
    return f"{compiler.process(column, **kw)}->>{compiler.process(field, **kw)}"


class _JsonTopLevelKeyType(TypeDecorator[str]):
    """Bind a literal top-level JSON key for each supported database."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        """Convert DuckDB keys to JSON Pointer and leave PostgreSQL keys raw."""
        if value is None or dialect.name != "duckdb":
            return value
        return _to_json_pointer([value])


class _JsonStringType(TypeDecorator[str]):
    r"""Bind-parameter type that JSON-encodes strings on DuckDB only.

    DuckDB's ``json_extract`` returns JSON-encoded values, so comparison
    values must also be JSON-encoded to match.  PostgreSQL's ``->>``
    returns plain text, so strings pass through unchanged.

    Example for ``{"key": "value"}``:

    - DuckDB:      ``json_extract(data, '$.key')`` returns ``'"value"'``
                    -> bind param must be ``'"value"'`` (via ``json.dumps``)
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


def _parse_field_path(field: str) -> list[str | int]:
    """Split a field path into key and array-index segments.

    ``"a.list[0]"`` becomes ``["a", "list", 0]``. Bracket groups that do not hold an
    integer are kept as part of the key, so they cannot reach SQL as an index.
    """
    segments: list[str | int] = []
    # Split on '.' but keep bracket notation (e.g. "nested_list[0]" -> "nested_list", "[0]")
    for part in field.replace("[", ".[").split("."):
        index_match = _ARRAY_INDEX_PATTERN.match(part)
        segments.append(int(index_match.group(1)) if index_match else part)
    return segments


def _to_json_pointer(segments: Sequence[str | int]) -> str:
    """Join path segments into a JSON Pointer, escaping ``~`` and ``/`` in keys.

    ``["a", "b/c", 0]`` becomes ``"/a/b~1c/0"``. DuckDB reads this syntax, and unlike
    ``$.a.b`` it treats every segment literally, so dots in keys are not path syntax.
    """
    escaped = [
        str(segment) if isinstance(segment, int) else segment.replace("~", "~0").replace("/", "~1")
        for segment in segments
    ]
    return "/" + "/".join(escaped)


def _build_pg_json_accessor(
    column: str,
    segments: Sequence[BindParameter[str] | int],
    compiler: SQLCompiler,
    *,
    cast_to_float: bool = False,
    **kw: Any,
) -> str:
    """Build a PostgreSQL JSON accessor expression from path segments.

    Two key segments become a ``col->:key_1->>:key_2`` operator chain. The chain itself
    is structural, so each key is bound individually; integer indices render unquoted
    because PostgreSQL requires that form for array access.

    Args:
        column: Already-compiled column SQL string.
        segments: Bound key parameters and integer array indices, in path order.
        compiler: The active SQL compiler, used to render the bound keys.
        cast_to_float: If True, wrap the expression in ``(...)::float``.
        kw: Compilation keyword arguments forwarded to the compiler.

    Returns:
        A raw SQL expression string.
    """
    accessors: list[str] = []
    for i, segment in enumerate(segments):
        is_last = i == len(segments) - 1
        op = "->>" if is_last else "->"
        if isinstance(segment, int):
            accessors.append(f"{op}{segment}")
        else:
            accessors.append(f"{op}{compiler.process(segment, **kw)}")

    expr = column + "".join(accessors)
    if cast_to_float:
        expr = f"({expr})::float"
    return expr
