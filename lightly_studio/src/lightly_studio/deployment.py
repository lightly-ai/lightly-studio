"""The deployment: a local run or an enterprise server.

Use `is_enterprise()` to decide on enterprise behavior.
"""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.database.db_manager import DatabaseBackend


def is_enterprise(session: Session) -> bool:
    """Returns True if the server is an enterprise server.

    A local run uses DuckDB and an enterprise server uses PostgreSQL. The check uses the bind
    of the session, not the global engine, so it is correct in tests with per-test engines.

    Args:
        session: A session of the server database.
    """
    bind = session.get_bind()
    return bind.dialect.name == DatabaseBackend.POSTGRESQL.value
