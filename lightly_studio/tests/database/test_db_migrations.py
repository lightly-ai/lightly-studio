"""Tests for PostgreSQL Alembic startup."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from pytest_mock import MockerFixture
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from lightly_studio.database import db_migrations, db_url
from lightly_studio.database.db_manager import DatabaseEngine

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


def test_postgres_embedding_model_dataset_id__backfilled(
    postgres_url: str | None,
) -> None:
    """The dataset ID migration backfills embedding models from their collection."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    collection_id = "00000000-0000-0000-0000-000000000002"

    try:
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="b1c2d3e4f5a6",
        )
        with engine.begin() as connection:
            connection.execute(
                statement=text("INSERT INTO dataset (dataset_id) VALUES (:dataset_id)"),
                parameters={"dataset_id": dataset_id},
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO collection (
                        name, sample_type, collection_id, dataset_id, created_at, updated_at
                    ) VALUES (
                        'collection', 'IMAGE', :collection_id, :dataset_id, NOW(), NOW()
                    )
                    """
                ),
                parameters={"collection_id": collection_id, "dataset_id": dataset_id},
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO embedding_model (
                        name, embedding_dimension, collection_id, embedding_model_id, created_at
                    ) VALUES (
                        'model', 128, :collection_id,
                        '00000000-0000-0000-0000-000000000003', NOW()
                    )
                    """
                ),
                parameters={"collection_id": collection_id},
            )

        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="head",
        )
        with engine.connect() as connection:
            backfilled_dataset_id = connection.execute(
                statement=text("SELECT dataset_id FROM embedding_model")
            ).scalar_one()
        assert str(backfilled_dataset_id) == dataset_id

        config.attributes.pop("connection", None)
        command.check(config)
    finally:
        engine.dispose()
