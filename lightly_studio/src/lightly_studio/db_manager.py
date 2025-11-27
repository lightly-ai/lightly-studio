"""Module provides functions to initialize and manage the DuckDB."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
from sqlmodel import Session, SQLModel, create_engine
from typing_extensions import Annotated

import lightly_studio.api.db_tables  # noqa: F401, required for SQLModel to work properly


class DatabaseEngine:
    """Database engine wrapper."""

    _engine_url: str
    _engine: Engine
    _persistent_session: Session | None = None

    def __init__(
        self,
        engine_url: str | None = None,
        cleanup_existing: bool = False,
        poolclass: type[Pool] | None = None,
    ) -> None:
        """Create a new instance of the DatabaseEngine.

        Args:
            engine_url: The database engine URL. If None, defaults to a local DuckDB file.
            cleanup_existing: If True, deletes the existing database file if it exists.
            poolclass: The SQLAlchemy pool class to use. Use StaticPool for
                in-memory databases for testing, otherwise different DB connections
                connect to different in-memory databases.
        """
        self._engine_url = engine_url if engine_url else "duckdb:///lightly_studio.db"
        if cleanup_existing:
            _cleanup_database_file(engine_url=self._engine_url)
        # Total available connections = pool_size + max_overflow = 20 + 40 = 60
        # (default is (pool_size=5, max_overflow=10))
        self._engine = create_engine(
            url=self._engine_url,
            poolclass=poolclass,
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


# Global database engine instance instantiated lazily.
_engine: DatabaseEngine | None = None


def get_engine() -> DatabaseEngine:
    """Get the database engine.

    If the engine does not exist yet, it is newly created with the default settings.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = DatabaseEngine()
    return _engine


def set_engine(engine: DatabaseEngine) -> None:
    """Set the database engine."""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        raise RuntimeError("Database engine is already set and cannot be changed.")
    _engine = engine


def connect(db_file: str | None = None, cleanup_existing: bool = False) -> None:
    """Set up the database connection.

    Helper function to set up the database engine.

    Args:
        db_file: The path to the DuckDB file. If None, uses a default, see DatabaseEngine class.
        cleanup_existing: If True, deletes the pre-existing database file if a file database
            is used.
    """
    engine_url = f"duckdb:///{db_file}" if db_file is not None else None
    engine = DatabaseEngine(engine_url=engine_url, cleanup_existing=cleanup_existing)
    set_engine(engine=engine)


@contextmanager
def session() -> Generator[Session, None, None]:
    """Create a short-lived database session. The session is autoclosed."""
    with get_engine().session() as session:
        yield session


def persistent_session() -> Session:
    """Create a persistent session."""
    return get_engine().get_persistent_session()


def _cleanup_database_file(engine_url: str) -> None:
    """Delete database file if it exists.

    Args:
        engine_url: The database engine URL
    """
    db_file = Path(engine_url.replace("duckdb:///", ""))
    if db_file.exists() and db_file.is_file():
        db_file.unlink()
        logging.info(f"Deleted existing database: {db_file}")


def _session_dependency() -> Generator[Session, None, None]:
    """Session dependency for FastAPI routes.

    We need to convert the context manager to a generator.
    """
    with session() as sess:
        yield sess


SessionDep = Annotated[Session, Depends(_session_dependency)]
