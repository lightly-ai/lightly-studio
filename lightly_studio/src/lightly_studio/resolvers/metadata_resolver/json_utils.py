"""Dialect-aware JSON extraction helpers for metadata queries.

Provides functions that return raw SQL expression strings for extracting values
from JSON columns, dispatching to the correct syntax based on the active
database backend (DuckDB ``json_extract()`` vs PostgreSQL ``->>``/``->``).
"""

from lightly_studio import db_manager
from lightly_studio.db_manager import DatabaseBackend

# Default metadata column name used across metadata resolvers.
METADATA_COLUMN = "metadata.data"


def _build_pg_json_accessor(column: str, field: str, *, cast_to_float: bool = False) -> str:
    """Build a PostgreSQL JSON accessor expression from a dot-separated field path.

    Converts paths like ``dict.key`` to PostgreSQL ``->``/``->>`` operator chains.

    Args:
        column: The fully-qualified column reference (e.g. ``metadata.data``).
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


def json_extract_sql(
    field: str, *, column: str = METADATA_COLUMN, cast_to_float: bool = False
) -> str:
    """Return a raw SQL expression for extracting a JSON value.

    Dispatches to the correct syntax based on the active database backend.

    Args:
        field: Dot-separated path into the JSON object (e.g. ``"temperature"``
            or ``"test_dict.int_key"``).
        column: The fully-qualified column reference. Defaults to
            :data:`METADATA_COLUMN`.
        cast_to_float: If True, the extracted value is cast to a float.

    Returns:
        A raw SQL expression string.
    """
    backend = db_manager.get_backend()
    if backend == DatabaseBackend.POSTGRESQL:
        return _build_pg_json_accessor(column=column, field=field, cast_to_float=cast_to_float)
    json_path = "$." + field
    expr = f"json_extract({column}, '{json_path}')"
    return f"CAST({expr} AS FLOAT)" if cast_to_float else expr


def json_not_null_sql(field: str, *, column: str = METADATA_COLUMN) -> str:
    """Return a raw SQL expression for checking that a JSON field is not null.

    Args:
        field: Dot-separated path into the JSON object.
        column: The fully-qualified column reference. Defaults to
            :data:`METADATA_COLUMN`.

    Returns:
        A raw SQL expression string (e.g. ``"... IS NOT NULL"``).
    """
    backend = db_manager.get_backend()
    if backend == DatabaseBackend.POSTGRESQL:
        return f"{_build_pg_json_accessor(column=column, field=field)} IS NOT NULL"
    return f"json_extract({column}, '$.{field}') IS NOT NULL"
