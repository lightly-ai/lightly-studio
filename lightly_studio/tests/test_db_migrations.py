"""Tests for PostgreSQL Alembic startup."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from pytest_mock import MockerFixture
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from lightly_studio import db_migrations, db_url
from lightly_studio.db_manager import DatabaseEngine

_POSTGRES_URL = "postgresql://localhost/db"


@pytest.fixture
def engine() -> Engine:
    """In-memory SQLite engine for inspector helpers (no Postgres required)."""
    return create_engine("sqlite:///:memory:")


def test_run_migrations__upgrade_when_alembic_version_exists(
    mocker: MockerFixture,
    engine: Engine,
) -> None:
    """Tracked DB runs upgrade head only."""
    alembic_cfg = Config()
    mocker.patch.object(db_migrations, "get_alembic_config", return_value=alembic_cfg)
    mocker.patch.object(db_migrations, "_alembic_version_table_exists", return_value=True)
    mock_run_command = mocker.patch.object(db_migrations, "_run_alembic_command")

    db_migrations.run_migrations(engine=engine, engine_url=_POSTGRES_URL)

    mock_run_command.assert_called_once_with(
        engine=engine,
        config=alembic_cfg,
        fn=command.upgrade,
        revision="head",
    )


def test_run_migrations__fresh_database(
    mocker: MockerFixture,
    engine: Engine,
) -> None:
    """Empty DB runs upgrade head (Alembic revisions only)."""
    alembic_cfg = Config()
    mocker.patch.object(db_migrations, "get_alembic_config", return_value=alembic_cfg)
    mocker.patch.object(db_migrations, "_alembic_version_table_exists", return_value=False)
    mock_run_command = mocker.patch.object(db_migrations, "_run_alembic_command")

    db_migrations.run_migrations(engine=engine, engine_url=_POSTGRES_URL)

    mock_run_command.assert_called_once_with(
        engine=engine,
        config=alembic_cfg,
        fn=command.upgrade,
        revision="head",
    )


def _reset_postgres_database(engine_url: str) -> None:
    """Drop application tables and Alembic version tracking."""
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=engine_url)
    raw_engine = create_engine(normalized_url)
    try:
        SQLModel.metadata.drop_all(bind=raw_engine)
        with raw_engine.connect() as conn:
            conn.execute(statement=text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
    finally:
        raw_engine.dispose()


def test_postgres_fresh_database__upgrade_head(
    postgres_url: str | None,
) -> None:
    """Fresh Postgres gets schema from Alembic upgrade and alembic_version at head."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)

    engine = DatabaseEngine(engine_url=postgres_url, single_threaded=True)
    try:
        head_revision = db_migrations.get_head_revision()

        inspector = db_migrations._get_inspector(engine=engine._engine)
        assert inspector.has_table(table_name="collection")
        assert inspector.has_table(table_name="alembic_version")

        with engine.session() as session:
            version = session.execute(
                statement=text("SELECT version_num FROM alembic_version"),
            ).scalar_one()
        assert version == head_revision
    finally:
        engine.close()
