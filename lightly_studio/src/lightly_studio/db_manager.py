"""Module provides functions to initialize and manage the database.

Supports both DuckDB and PostgreSQL backends. The backend is determined by:
1. Explicit engine_url parameter
2. LIGHTLY_STUDIO_DATABASE_URL environment variable
3. Default: DuckDB (duckdb:///lightly_studio.db)

Examples:
    - DuckDB: "duckdb:///lightly_studio.db"
    - PostgreSQL: "postgresql://user:pass@localhost:5432/dbname"
"""

from __future__ import annotations

import atexit
import logging
import re
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import StaticPool, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

import lightly_studio.api.db_tables  # noqa: F401, required for SQLModel to work properly
from lightly_studio.dataset.env import LIGHTLY_STUDIO_DATABASE_URL


class DatabaseBackend(str, Enum):
    """The type of database backend."""

    DUCKDB = "duckdb"
    POSTGRESQL = "postgresql"


class DatabaseEngine:
    """Database engine wrapper."""

    _engine_url: str
    _engine: Engine
    _persistent_session: Session | None = None
    _backend: DatabaseBackend

    def __init__(
        self,
        engine_url: str | None = None,
        cleanup_existing: bool = False,
        single_threaded: bool = False,
    ) -> None:
        """Create a new instance of the DatabaseEngine.

        Args:
            engine_url: The database engine URL. If None, reads from LIGHTLY_STUDIO_DATABASE_URL
                env var, or defaults to a local DuckDB file.
            cleanup_existing: If True, deletes the existing database file if it exists.
                Only applicable for DuckDB.
            single_threaded: If True, creates a single-threaded engine suitable for testing.
        """
        if engine_url is not None:
            self._engine_url = engine_url
        elif LIGHTLY_STUDIO_DATABASE_URL is not None:
            self._engine_url = LIGHTLY_STUDIO_DATABASE_URL
        else:
            self._engine_url = "duckdb:///lightly_studio.db"

        self._backend = _detect_backend_from_url(self._engine_url)

        # Ensure the psycopg3 driver is used for Postgres connections.
        if self._backend == DatabaseBackend.POSTGRESQL:
            self._engine_url = _ensure_psycopg3_driver(self._engine_url)

        # TODO (Mihnea, 02/2026): Support cleanup for Postgres too.
        if cleanup_existing and self._backend == DatabaseBackend.DUCKDB:
            _cleanup_database_file(engine_url=self._engine_url)

        if single_threaded:
            self._engine = create_engine(
                url=self._engine_url,
                poolclass=StaticPool,
            )
        else:
            # TODO(Mihnea, 02/2026): Consider adding Postgres-specific pool options
            self._engine = create_engine(
                url=self._engine_url,
                pool_size=10,
                max_overflow=40,
            )

        if self._backend == DatabaseBackend.POSTGRESQL:
            with self._engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()

        SQLModel.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a short-lived database session. The session is autoclosed."""
        # Commit the persistent session before creating a short-lived session.
        # This prevents a foreign key constraint violation issue if the short-lived
        # session attempts a delete of an object referencing an object modified
        # in the persistent session.
        # TODO(Mihnea, 02/2026): Consider making this DuckDB specific,
        #  as this won't be a problem in Postgres.
        if self.get_persistent_session().in_transaction():
            logging.debug("The persistent session is in transaction, committing changes.")
            self.get_persistent_session().commit()

        session = Session(self._engine, close_resets_only=False)
        try:
            yield session
            session.commit()

            # Commit the persistent session to ensure it sees the latest data changes.
            # This prevents the persistent session from having stale data when it's used
            # after operations in short-lived sessions have modified the database.
            self.get_persistent_session().commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @property
    def backend(self) -> DatabaseBackend:
        """Get the database backend type."""
        return self._backend

    def get_persistent_session(self) -> Session:
        """Get the persistent database session."""
        if self._persistent_session is None:
            self._persistent_session = Session(
                self._engine, close_resets_only=False, expire_on_commit=True
            )
        return self._persistent_session

    def close(self) -> None:
        """Close the persistent session and dispose the engine."""
        if self._persistent_session is not None:
            try:
                if self._persistent_session.in_transaction():
                    logging.debug(
                        "The persistent session is in transaction, committing before close."
                    )
                    self._persistent_session.commit()
            finally:
                self._persistent_session.close()
                self._persistent_session = None

        self._engine.dispose()


# Global database engine instance instantiated lazily.
_engine: DatabaseEngine | None = None


def get_engine() -> DatabaseEngine:
    """Get the database engine.

    If the engine does not exist yet, it is newly created with the default settings.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = DatabaseEngine()
        atexit.register(close)
    return _engine


def set_engine(engine: DatabaseEngine) -> None:
    """Set the database engine."""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        raise RuntimeError("Database engine is already set and cannot be changed.")
    _engine = engine
    atexit.register(close)


def connect(
    db_file: str | None = None,
    cleanup_existing: bool = False,
    engine_url: str | None = None,
) -> None:
    """Set up the database connection.

    Helper function to set up the database engine. Supports both DuckDB (default)
    and PostgreSQL via the engine_url parameter or LIGHTLY_STUDIO_DATABASE_URL env var.

    Args:
        db_file: Path to DuckDB file.
        cleanup_existing: If True, deletes existing database file (DuckDB only).
        engine_url: Full database URL.

    Raises:
        ValueError: If both db_file and engine_url are provided.
    """
    if db_file is not None and engine_url is not None:
        raise ValueError("Cannot specify both db_file and engine_url")

    if engine_url is None and db_file is not None:
        engine_url = f"duckdb:///{db_file}"

    engine = DatabaseEngine(
        engine_url=engine_url,
        cleanup_existing=cleanup_existing,
    )
    set_engine(engine=engine)


@contextmanager
def session() -> Generator[Session, None, None]:
    """Create a short-lived database session. The session is autoclosed."""
    with get_engine().session() as session:
        yield session


def persistent_session() -> Session:
    """Create a persistent session."""
    return get_engine().get_persistent_session()


def close() -> None:
    """Close the database engine and reset the global reference."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        return
    _engine.close()
    _engine = None


def get_backend() -> DatabaseBackend:
    """Get the current database backend type."""
    return get_engine().backend


def _detect_backend_from_url(engine_url: str) -> DatabaseBackend:
    """Detect the database backend from the engine URL.

    Args:
        engine_url: The database engine URL.

    Returns:
        The detected DatabaseBackend.

    Raises:
        ValueError: If the URL scheme is not supported.
    """
    if engine_url.startswith("duckdb://"):
        return DatabaseBackend.DUCKDB
    if engine_url.startswith(("postgresql://", "postgres://")):
        return DatabaseBackend.POSTGRESQL
    raise ValueError(
        f"Unsupported database URL scheme: {engine_url}. "
        f"Supported schemes: duckdb://, postgresql://, postgres://"
    )


def _ensure_psycopg3_driver(engine_url: str) -> str:
    """Ensure the psycopg3 driver is specified in a PostgreSQL URL.

    SQLAlchemy defaults to psycopg2 for ``postgresql://`` URLs. This rewrites
    the URL to use ``postgresql+psycopg://`` so that the psycopg3 driver is
    selected instead.

    Args:
        engine_url: The database engine URL.

    Returns:
        The URL with the psycopg3 driver specified.
    """
    # Only rewrite if no explicit driver is specified.
    return re.sub(r"^(postgresql|postgres)://", "postgresql+psycopg://", engine_url)


def _cleanup_database_file(engine_url: str) -> None:
    """Delete database file if it exists.

    Args:
        engine_url: The database engine URL
    """
    db_file = Path(engine_url.replace("duckdb:///", ""))
    cleanup_paths = [
        db_file,
        db_file.with_name(f"{db_file.name}.wal"),
        db_file.with_name(f"{db_file.name}.tmp"),
    ]
    for path in cleanup_paths:
        if path.exists() and path.is_file():
            path.unlink()
            logging.info(f"Deleted existing database file: {path}")


def _session_dependency() -> Generator[Session, None, None]:
    """Session dependency for FastAPI routes.

    We need to convert the context manager to a generator.
    """
    with session() as sess:
        yield sess


SessionDep = Annotated[Session, Depends(_session_dependency)]
