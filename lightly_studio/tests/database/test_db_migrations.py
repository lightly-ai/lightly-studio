"""Tests for PostgreSQL Alembic startup."""

from __future__ import annotations

import json

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


def _restore_shared_database_to_head(engine: Engine, engine_url: str) -> None:
    """Return the session-scoped Postgres database to a clean schema at head.

    These migration tests run against the ``postgres_url`` database, which is session
    scoped and shared with every data test on the same xdist worker. A test that
    downgrades or resets that database leaves the schema off head, so the data tests find
    the wrong tables and their ``TRUNCATE`` teardown fails. Upgrading to head first
    normalizes the table names (a downgrade may have renamed one), then a drop and a fresh
    upgrade leave an empty schema matching the session engine's initial state.
    """
    config = db_migrations.get_alembic_config(engine_url=engine_url)
    db_migrations._run_alembic_command(
        engine=engine, config=config, fn=command.upgrade, revision="head"
    )
    _reset_postgres_database(engine_url=engine_url)
    db_migrations._run_alembic_command(
        engine=engine, config=config, fn=command.upgrade, revision="head"
    )


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
        _restore_shared_database_to_head(engine=engine._engine, engine_url=postgres_url)
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
        columns = db_migrations._get_inspector(engine=engine).get_columns(
            table_name="embedding_model"
        )
        dataset_id_column = next(column for column in columns if column["name"] == "dataset_id")
        assert dataset_id_column["nullable"] is False

        config.attributes.pop("connection", None)
        command.check(config)
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_collection_embedding_model__backfills_all_models(
    postgres_url: str | None,
) -> None:
    """The rename migration seeds every embedding model, the oldest one as default."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    collection_id = "00000000-0000-0000-0000-000000000002"
    older_model_id = "00000000-0000-0000-0000-000000000010"
    newer_model_id = "00000000-0000-0000-0000-000000000011"

    try:
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="c2d3e4f5a6b7",
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
            # Two models for the same collection; the older one must become the default.
            connection.execute(
                statement=text(
                    """
                    INSERT INTO embedding_model (
                        name, embedding_dimension, collection_id, dataset_id,
                        embedding_model_id, created_at
                    ) VALUES (
                        'older', 128, :collection_id, :dataset_id,
                        :older_model_id, '2020-01-01 00:00:00+00'
                    ), (
                        'newer', 128, :collection_id, :dataset_id,
                        :newer_model_id, '2021-01-01 00:00:00+00'
                    )
                    """
                ),
                parameters={
                    "collection_id": collection_id,
                    "dataset_id": dataset_id,
                    "older_model_id": older_model_id,
                    "newer_model_id": newer_model_id,
                },
            )

        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="d4e5f6a7b8c9",
        )
        with engine.connect() as connection:
            rows = connection.execute(
                statement=text(
                    """
                    SELECT embedding_model_id, is_default
                    FROM collection_embedding_model
                    WHERE collection_id = :collection_id
                    ORDER BY embedding_model_id
                    """
                ),
                parameters={"collection_id": collection_id},
            ).all()

        defaults = {str(model_id): is_default for model_id, is_default in rows}
        assert defaults == {older_model_id: True, newer_model_id: False}

        # Downgrade must keep only the default row so the collection-only key holds.
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.downgrade,
            revision="c2d3e4f5a6b7",
        )
        with engine.connect() as connection:
            remaining = connection.execute(
                statement=text(
                    """
                    SELECT embedding_model_id
                    FROM default_embedding_space
                    WHERE collection_id = :collection_id
                    """
                ),
                parameters={"collection_id": collection_id},
            ).all()
        assert [str(model_id) for (model_id,) in remaining] == [older_model_id]
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_metadata__json_jsonb_migration(
    postgres_url: str | None,
) -> None:
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    collection_id = "00000000-0000-0000-0000-000000000002"
    sample_id = "00000000-0000-0000-0000-000000000003"
    # Cover nested values, arrays, a JSON null, and a dotted key.
    data = {"nested": {"scores": [1, 2, 3]}, "flag": True, "missing": None, "dotted.key": "value"}
    metadata_schema = {
        "nested": "dict",
        "flag": "boolean",
        "missing": "null",
        "dotted.key": "string",
    }

    try:
        # Upgrade to the revision just before the JSONB conversion, where the columns are json.
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="c5d6e7f8a9b0"
        )
        assert _metadata_column_data_type(engine=engine, column_name="data") == "json"

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
                    INSERT INTO sample (collection_id, sample_id, created_at, updated_at)
                    VALUES (:collection_id, :sample_id, NOW(), NOW())
                    """
                ),
                parameters={"collection_id": collection_id, "sample_id": sample_id},
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO metadata (
                        custom_metadata_id, sample_id, created_at, updated_at,
                        data, metadata_schema
                    ) VALUES (
                        gen_random_uuid(), :sample_id, NOW(), NOW(),
                        CAST(:data AS json), CAST(:metadata_schema AS json)
                    )
                    """
                ),
                parameters={
                    "sample_id": sample_id,
                    "data": json.dumps(data),
                    "metadata_schema": json.dumps(metadata_schema),
                },
            )

        # Upgrade across the JSONB conversion.
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="head"
        )
        assert _metadata_column_data_type(engine=engine, column_name="data") == "jsonb"
        assert _metadata_column_data_type(engine=engine, column_name="metadata_schema") == "jsonb"
        columns = db_migrations._get_inspector(engine=engine).get_columns(table_name="metadata")
        for column in columns:
            if column["name"] in ("data", "metadata_schema"):
                assert column["nullable"] is False

        # The stored values survive the conversion (psycopg parses jsonb back into Python objects).
        with engine.connect() as connection:
            stored_data, stored_schema = connection.execute(
                statement=text("SELECT data, metadata_schema FROM metadata")
            ).one()
        assert stored_data == data
        assert stored_schema == metadata_schema

        config.attributes.pop("connection", None)
        command.check(config)

        # The downgrade restores json storage and keeps the values.
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.downgrade, revision="c5d6e7f8a9b0"
        )
        assert _metadata_column_data_type(engine=engine, column_name="data") == "json"
        with engine.connect() as connection:
            downgraded_data = connection.execute(
                statement=text("SELECT data FROM metadata")
            ).scalar_one()
        assert downgraded_data == data
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_embedding_model_api_key__added_and_dropped(
    postgres_url: str | None,
) -> None:
    """The API key migration adds a nullable column and the downgrade removes it again."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    model_id = "00000000-0000-0000-0000-000000000003"

    try:
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="a2b3c4d5e6f7",
        )
        with engine.begin() as connection:
            connection.execute(
                statement=text("INSERT INTO dataset (dataset_id) VALUES (:dataset_id)"),
                parameters={"dataset_id": dataset_id},
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO embedding_model (
                        name, embedding_dimension, dataset_id, embedding_model_id, created_at
                    ) VALUES (
                        'model', 128, :dataset_id, :model_id, NOW()
                    )
                    """
                ),
                parameters={"dataset_id": dataset_id, "model_id": model_id},
            )

        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="head",
        )
        columns = db_migrations._get_inspector(engine=engine).get_columns(
            table_name="embedding_model"
        )
        api_key_column = next(column for column in columns if column["name"] == "api_key")
        assert api_key_column["nullable"] is True

        # The existing row needs no backfill, and the column accepts a key.
        with engine.begin() as connection:
            assert (
                connection.execute(
                    statement=text("SELECT api_key FROM embedding_model")
                ).scalar_one()
                is None
            )
            connection.execute(
                statement=text("UPDATE embedding_model SET api_key = 'secret'"),
            )

        config.attributes.pop("connection", None)
        command.check(config)

        # The downgrade drops the column and keeps the row.
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.downgrade,
            revision="a2b3c4d5e6f7",
        )
        columns = db_migrations._get_inspector(engine=engine).get_columns(
            table_name="embedding_model"
        )
        assert "api_key" not in {column["name"] for column in columns}
        with engine.connect() as connection:
            remaining = connection.execute(
                statement=text("SELECT embedding_model_id FROM embedding_model")
            ).scalar_one()
        assert str(remaining) == model_id
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def _metadata_column_data_type(engine: Engine, column_name: str) -> str:
    """Return the SQL ``data_type`` of a ``metadata`` column, e.g. ``json`` or ``jsonb``."""
    with engine.connect() as connection:
        data_type = connection.execute(
            statement=text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'metadata' AND column_name = :column_name"
            ),
            parameters={"column_name": column_name},
        ).scalar_one()
    assert isinstance(data_type, str)
    return data_type
