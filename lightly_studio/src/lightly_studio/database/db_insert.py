"""Dialect-aware bulk ``INSERT`` that ignores rows conflicting with existing keys.

Uses PostgreSQL ``ON CONFLICT DO NOTHING`` and DuckDB/SQLite ``OR IGNORE``, batched to
stay under PostgreSQL's bind-parameter cap.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, SQLModel

from lightly_studio.utils import batching


def insert_ignoring_conflicts(
    session: Session,
    table: type[SQLModel],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Bulk-insert ``rows`` (column-to-value mappings) into ``table`` in batches.

    Skips rows colliding with a unique or primary-key constraint, so deduplicate in the
    caller where needed. Does not commit or flush; the caller owns the transaction.
    No-op for empty ``rows``.
    """
    if not rows:
        return

    bind = session.get_bind()
    dialect_name = bind.dialect.name if bind is not None else None
    for batch in batching.batched(items=rows):
        if dialect_name == "postgresql":
            session.exec(pg_insert(table).values(batch).on_conflict_do_nothing())
        else:  # DuckDB and SQLite
            session.exec(insert(table).values(batch).prefix_with("OR IGNORE"))
