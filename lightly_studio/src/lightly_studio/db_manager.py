"""Module provides functions to initialize and manage the database.

Supports both DuckDB (default) and PostgreSQL backends via DATABASE_URL.
"""

from __future__ import annotations

import atexit
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from fastapi import Depends
from sqlalchemy import StaticPool
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine
from typing_extensions import Annotated

import lightly_studio.api.db_tables  # noqa: F401, required for SQLModel to work properly

# Environment variable for database URL
DATABASE_URL = "DATABASE_URL"
DEFAULT_DUCKDB_URL = "duckdb:///lightly_studio.db"


class DatabaseEngine:
    """Database engine wrapper.

    Supports both DuckDB and PostgreSQL backends. The backend is determined by the
    DATABASE_URL environment variable or the engine_url parameter.

    Examples:
        - DuckDB: "duckdb:///lightly_studio.db" (default)
        - PostgreSQL: "postgresql://user:pass@localhost:5432/dbname"
    """

    _engine_url: str
    _engine: Engine
    _persistent_session: Session | None = None

    def __init__(
        self,
        engine_url: str | None = None,
        cleanup_existing: bool = False,
        single_threaded: bool = False,
    ) -> None:
        """Create a new instance of the DatabaseEngine.

        Args:
            engine_url: The database engine URL. If None, reads from DATABASE_URL env var,
                        or defaults to a local DuckDB file.
            cleanup_existing: If True, deletes the existing database file if it exists.
                              Only applies to file-based databases (DuckDB).
            single_threaded: If True, creates a single-threaded engine suitable for testing.
        """
        if engine_url:
            self._engine_url = engine_url
        else:
            self._engine_url = os.environ.get(DATABASE_URL, DEFAULT_DUCKDB_URL)

        # Only cleanup for file-based databases (DuckDB)
        if cleanup_existing and self.is_duckdb:
            _cleanup_database_file(engine_url=self._engine_url)

        if single_threaded:
            self._engine = create_engine(
                url=self._engine_url,
                poolclass=StaticPool,
            )
        else:
            self._engine = create_engine(
                url=self._engine_url,
                pool_size=10,
                max_overflow=40,
            )

        SQLModel.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a short-lived database session. The session is autoclosed."""
        # Commit the persistent session before creating a short-lived session.
        # This prevents a foreign key constraint violation issue if the short-lived
        # session attempts a delete of an object referencing an object modified
        # in the persistent session.
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

    def get_persistent_session(self) -> Session:
        """Get the persistent database session."""
        if self._persistent_session is None:
            self._persistent_session = Session(
                self._engine, close_resets_only=False, expire_on_commit=True
            )
        return self._persistent_session

    @property
    def is_duckdb(self) -> bool:
        """Check if the database backend is DuckDB."""
        return self._engine_url.startswith("duckdb://")

    @property
    def is_postgresql(self) -> bool:
        """Check if the database backend is PostgreSQL."""
        return self._engine_url.startswith("postgresql://")

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
    and PostgreSQL via the engine_url parameter or DATABASE_URL env var.

    Args:
        db_file: The path to the DuckDB file. If None, uses DATABASE_URL env var or default.
                 Ignored if engine_url is provided.
        cleanup_existing: If True, deletes the pre-existing database file if a file database
            is used. Only applies to DuckDB.
        engine_url: Full database URL (e.g., "postgresql://user:pass@host:port/db").
                    Takes precedence over db_file.
    """
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


def is_postgresql() -> bool:
    """Check if the current database backend is PostgreSQL.

    Returns:
        True if using PostgreSQL, False otherwise (e.g., DuckDB).
    """
    return get_engine().is_postgresql


def is_duckdb() -> bool:
    """Check if the current database backend is DuckDB.

    Returns:
        True if using DuckDB, False otherwise.
    """
    return get_engine().is_duckdb


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
