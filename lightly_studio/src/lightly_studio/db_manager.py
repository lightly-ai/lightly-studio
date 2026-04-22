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
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

import sqlalchemy_utils
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


@dataclass(frozen=True)
class _DatabaseInitState:
    """Initialization state for a DatabaseEngine instance."""

    engine_url: str
    backend: DatabaseBackend
    database_exists: bool
    cleanup_existing: bool
    must_exist: bool
    single_threaded: bool

    @classmethod
    def create(
        cls,
        *,
        engine_url: str | None,
        cleanup_existing: bool,
        must_exist: bool,
        single_threaded: bool,
    ) -> _DatabaseInitState:
        """Build the initialization state for a DatabaseEngine instance."""
        resolved_engine_url = cls._resolve_engine_url(engine_url=engine_url)
        backend = cls.detect_backend_from_url(engine_url=resolved_engine_url)
        if backend == DatabaseBackend.POSTGRESQL:
            resolved_engine_url = cls._ensure_psycopg3_driver(engine_url=resolved_engine_url)

        database_exists = cls._database_exists(
            engine_url=resolved_engine_url,
            backend=backend,
        )
        return cls(
            engine_url=resolved_engine_url,
            backend=backend,
            database_exists=database_exists,
            cleanup_existing=cleanup_existing,
            must_exist=must_exist,
            single_threaded=single_threaded,
        )

    def validate_must_exist(self) -> None:
        """Raise if the database must exist but does not."""
        if self.must_exist and not self.database_exists:
            raise FileNotFoundError(f"Database does not exist at {self.engine_url}.")

    def cleanup_existing_duckdb_database(self) -> None:
        """Delete the DuckDB database files when cleanup is requested."""
        if not self.cleanup_existing or self.backend != DatabaseBackend.DUCKDB:
            return
        self._cleanup_database_file(engine_url=self.engine_url)

    def create_sqlalchemy_engine(self) -> Engine:
        """Create the SQLAlchemy engine for the configured database."""
        if self.single_threaded:
            return create_engine(
                url=self.engine_url,
                poolclass=StaticPool,
            )

        # TODO(Mihnea, 02/2026): Consider adding Postgres-specific pool options
        return create_engine(
            url=self.engine_url,
            pool_size=10,
            max_overflow=40,
        )

    def initialize_postgresql_database(self, engine: Engine) -> None:
        """Create and initialize PostgreSQL-specific database state."""
        if self.backend != DatabaseBackend.POSTGRESQL:
            return

        # For DuckDB, create_engine will create the database file if it does not exist.
        # For Postgres, we need to create the database.
        if not self.database_exists:
            sqlalchemy_utils.create_database(self.engine_url)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

    def reset_schema_if_requested(self, engine: Engine) -> None:
        """Drop existing PostgreSQL tables when cleanup is requested."""
        if not self.cleanup_existing or self.backend != DatabaseBackend.POSTGRESQL:
            return

        SQLModel.metadata.drop_all(bind=engine)
        logging.info("Dropped all tables in PostgreSQL database.")

    @staticmethod
    def _resolve_engine_url(engine_url: str | None) -> str:
        """Resolve the database engine URL from the explicit value, env var, or default."""
        if engine_url is not None:
            return engine_url
        if LIGHTLY_STUDIO_DATABASE_URL is not None:
            return LIGHTLY_STUDIO_DATABASE_URL
        return "duckdb:///lightly_studio.db"

    @staticmethod
    def detect_backend_from_url(engine_url: str) -> DatabaseBackend:
        """Detect the database backend from the engine URL."""
        if engine_url.startswith("duckdb"):
            return DatabaseBackend.DUCKDB
        if engine_url.startswith("postgres"):
            return DatabaseBackend.POSTGRESQL
        raise ValueError(
            f"Unsupported database URL scheme: {engine_url}. "
            f"Supported schemes: duckdb://, postgresql://, postgres://"
        )

    @staticmethod
    def _ensure_psycopg3_driver(engine_url: str) -> str:
        """Ensure the psycopg3 driver is specified in a PostgreSQL URL."""
        # Only rewrite if no explicit driver is specified.
        return re.sub(r"^(postgresql|postgres)://", "postgresql+psycopg://", engine_url)

    @staticmethod
    def _database_exists(engine_url: str, backend: DatabaseBackend) -> bool:
        """Check if the configured database already exists."""
        # `sqlalchemy_utils.database_exists` does not support DuckDB, the backend always
        # creates a new database.
        if backend == DatabaseBackend.DUCKDB:
            db_path = engine_url.replace("duckdb:///", "")
            if db_path == ":memory:":
                return True
            return Path(db_path).exists()
        return bool(sqlalchemy_utils.database_exists(engine_url))

    @staticmethod
    def _cleanup_database_file(engine_url: str) -> None:
        """Delete database file if it exists."""
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
        must_exist: bool = False,
        single_threaded: bool = False,
    ) -> None:
        """Create a new instance of the DatabaseEngine.

        Args:
            engine_url: The database engine URL. If None, reads from LIGHTLY_STUDIO_DATABASE_URL
                env var, or defaults to a local DuckDB file.
            cleanup_existing: If True, removes the existing database before use.
            must_exist: If True, raises FileNotFoundError when the database does not exist.
            single_threaded: If True, creates a single-threaded engine suitable for testing.

        Raises:
            FileNotFoundError: If must_exist is True and the database does not exist.
        """
        init_state = _DatabaseInitState.create(
            engine_url=engine_url,
            cleanup_existing=cleanup_existing,
            must_exist=must_exist,
            single_threaded=single_threaded,
        )
        init_state.validate_must_exist()

        self._engine_url = init_state.engine_url
        self._backend = init_state.backend

        init_state.cleanup_existing_duckdb_database()
        self._engine = init_state.create_sqlalchemy_engine()
        init_state.initialize_postgresql_database(engine=self._engine)
        init_state.reset_schema_if_requested(engine=self._engine)
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

            if session.in_transaction():
                session.commit()

            # Commit the persistent session if it has an active transaction.
            # This ensures the session sees the latest data changes made by short-lived sessions.
            persistent_session = self.get_persistent_session()
            if persistent_session.in_transaction():
                persistent_session.commit()
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
    cleanup_existing: bool = False,
    must_exist: bool = False,
    db_file: str | None = None,
    db_url: str | None = None,
) -> None:
    """Set up the database connection.

    Helper function to set up the database engine. Supports both DuckDB (default)
    and PostgreSQL via the db_url parameter or LIGHTLY_STUDIO_DATABASE_URL env var.

    Args:
        cleanup_existing: If True, removes the existing database before use.
        must_exist: If True, raises FileNotFoundError when the database does not exist.
        db_file: Path to DuckDB file.
        db_url: Full database URL.

    Raises:
        ValueError: If both db_file and db_url are provided.
    """
    if db_file is not None and db_url is not None:
        raise ValueError("Cannot specify both db_file and db_url")

    if db_url is None and db_file is not None:
        db_url = f"duckdb:///{db_file}"

    engine = DatabaseEngine(
        engine_url=db_url,
        cleanup_existing=cleanup_existing,
        must_exist=must_exist,
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
    return _DatabaseInitState.detect_backend_from_url(engine_url=engine_url)


def _session_dependency() -> Generator[Session, None, None]:
    """Session dependency for FastAPI routes.

    We need to convert the context manager to a generator.
    """
    with session() as sess:
        yield sess


SessionDep = Annotated[Session, Depends(_session_dependency)]
