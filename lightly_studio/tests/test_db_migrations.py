"""Tests for PostgreSQL Alembic startup."""

from __future__ import annotations

import pytest
import sqlmodel
from alembic import command
from alembic.config import Config
from pytest_mock import MockerFixture
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from lightly_studio import db_manager, db_migrations, db_url
from lightly_studio.db_manager import DatabaseEngine
from lightly_studio.db_migrations import get_head_revision
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver

_POSTGRES_URL = "postgresql://localhost/db"


@pytest.fixture
def patch_engine_singleton(mocker: MockerFixture) -> None:
    """Reset the global engine singleton before db_manager.connect tests."""
    mocker.patch.object(db_manager, "_engine", new=None)


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
    mock_create_all = mocker.patch.object(SQLModel.metadata, "create_all")

    db_migrations.run_migrations(engine=engine, engine_url=_POSTGRES_URL)

    mock_run_command.assert_called_once_with(
        engine=engine,
        config=alembic_cfg,
        fn=command.upgrade,
        revision="head",
    )
    mock_create_all.assert_not_called()


def test_run_migrations__fresh_database(
    mocker: MockerFixture,
    engine: Engine,
) -> None:
    """Empty DB uses create_all then stamp head."""
    alembic_cfg = Config()
    mocker.patch.object(db_migrations, "get_alembic_config", return_value=alembic_cfg)
    mocker.patch.object(db_migrations, "_alembic_version_table_exists", return_value=False)
    mocker.patch.object(db_migrations, "_has_application_tables", return_value=False)
    mock_run_command = mocker.patch.object(db_migrations, "_run_alembic_command")
    mock_create_all = mocker.patch.object(SQLModel.metadata, "create_all")

    db_migrations.run_migrations(engine=engine, engine_url=_POSTGRES_URL)

    mock_create_all.assert_called_once_with(bind=engine)
    mock_run_command.assert_called_once_with(
        engine=engine,
        config=alembic_cfg,
        fn=command.stamp,
        revision="head",
    )


def test_run_migrations__legacy_database(
    mocker: MockerFixture,
    engine: Engine,
) -> None:
    """Pre-Alembic DB with tables is stamped head without create_all or upgrade."""
    alembic_cfg = Config()
    mocker.patch.object(db_migrations, "get_alembic_config", return_value=alembic_cfg)
    mocker.patch.object(db_migrations, "_alembic_version_table_exists", return_value=False)
    mocker.patch.object(db_migrations, "_has_application_tables", return_value=True)
    mock_run_command = mocker.patch.object(db_migrations, "_run_alembic_command")
    mock_create_all = mocker.patch.object(SQLModel.metadata, "create_all")

    db_migrations.run_migrations(engine=engine, engine_url=_POSTGRES_URL)

    mock_run_command.assert_called_once_with(
        engine=engine,
        config=alembic_cfg,
        fn=command.stamp,
        revision="head",
    )
    mock_create_all.assert_not_called()


def _reset_postgres_database(engine_url: str) -> None:
    """Drop application tables and Alembic version tracking."""
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=engine_url)
    raw_engine = create_engine(normalized_url)
    SQLModel.metadata.drop_all(bind=raw_engine)
    with raw_engine.connect() as conn:
        conn.execute(statement=text("DROP TABLE IF EXISTS alembic_version"))
        conn.commit()
    raw_engine.dispose()


def test_postgres_fresh_database__create_all_and_stamp(
    postgres_url: str | None,
) -> None:
    """Fresh Postgres gets tables and alembic_version at head."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)

    engine = DatabaseEngine(engine_url=postgres_url, single_threaded=True)
    head_revision = get_head_revision()

    inspector = db_migrations._get_inspector(engine=engine._engine)
    assert inspector.has_table(table_name="collection")
    assert inspector.has_table(table_name="alembic_version")

    with engine.session() as session:
        version = session.execute(
            statement=text("SELECT version_num FROM alembic_version"),
        ).scalar_one()
    assert version == head_revision
    engine.close()


def test_postgres_legacy_database__stamp_on_startup(
    postgres_url: str | None,
) -> None:
    """Pre-Alembic schema (create_all only) is adopted via stamp head on startup."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    raw_engine = create_engine(normalized_url)
    SQLModel.metadata.create_all(bind=raw_engine)
    assert not db_migrations._alembic_version_table_exists(engine=raw_engine)
    raw_engine.dispose()

    engine = DatabaseEngine(engine_url=postgres_url, single_threaded=True)
    head_revision = get_head_revision()

    with engine.session() as session:
        version = session.execute(
            statement=text("SELECT version_num FROM alembic_version"),
        ).scalar_one()
    assert version == head_revision
    engine.close()


def test_postgres_cleanup_existing__recreates_schema_at_head(
    postgres_url: str | None,
    patch_engine_singleton: None,  # noqa: ARG001
) -> None:
    """cleanup_existing drops schema and re-initializes with create_all + stamp head."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    head_revision = get_head_revision()

    db_manager.connect(db_url=postgres_url, cleanup_existing=False)
    with db_manager.session() as session:
        collection_resolver.create(
            session=session,
            collection=CollectionCreate(
                name="before_cleanup",
                sample_type=SampleType.IMAGE,
            ),
        )
    db_manager.close()

    db_manager.connect(db_url=postgres_url, cleanup_existing=True)
    with db_manager.session() as session:
        collections = session.exec(sqlmodel.select(CollectionTable)).all()
        assert collections == []
        version = session.execute(
            statement=text("SELECT version_num FROM alembic_version"),
        ).scalar_one()
    assert version == head_revision
    db_manager.close()


def test_postgres_upgrade_head_on_empty_database(
    postgres_url: str | None,
) -> None:
    """Empty Postgres can be brought to head via Alembic upgrade (CI migration-check path)."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    alembic_cfg = db_migrations.get_alembic_config(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    raw_engine = create_engine(normalized_url)

    with raw_engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, revision="head")

    head_revision = get_head_revision()
    inspector = db_migrations._get_inspector(engine=raw_engine)
    assert inspector.has_table(table_name="collection")
    assert inspector.has_table(table_name="alembic_version")

    with raw_engine.connect() as conn:
        version = conn.execute(
            statement=text("SELECT version_num FROM alembic_version"),
        ).scalar_one()
    assert version == head_revision
    raw_engine.dispose()
