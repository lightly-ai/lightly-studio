"""Tests for PostgreSQL Alembic startup."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from alembic import command
from alembic.config import Config
from pytest_mock import MockerFixture
from sqlalchemy import Column, Integer, Table, create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from lightly_studio.database import db_migrations, db_url
from lightly_studio.database.db_manager import DatabaseEngine
from lightly_studio.database.db_migrations import ExtensionMigrations
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.polygon import PolygonAnnotationTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
)

_POSTGRES_URL = "postgresql://localhost/db"

# The second, third and fourth lightly_studio revisions.
_OSS_REVISION_2 = "eeb98e205e86"
_OSS_REVISION_3 = "dc6fddd82c1c"
_OSS_REVISION_4 = "7e8b0d6c9a12"

# The env.py of a test extension. The version table of the extension is in the schema
# "ext". Alembic writes the version table before the first revision runs, so env.py
# creates the schema first.
_EXTENSION_ENV = """
from alembic import context
from sqlalchemy import text

connection = context.config.attributes["connection"]
connection.execute(text("CREATE SCHEMA IF NOT EXISTS ext"))
connection.commit()
context.configure(connection=connection, version_table_schema="ext")
with context.begin_transaction():
    context.run_migrations()
"""


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


@pytest.mark.parametrize(
    ("applied", "expected_upgrades"),
    [
        (
            None,
            [
                ("oss", _OSS_REVISION_2),
                ("ext", "ext0001"),
                ("oss", _OSS_REVISION_4),
                ("ext", "ext0002"),
                ("oss", "head"),
            ],
        ),
        ("ext0001", [("oss", _OSS_REVISION_4), ("ext", "ext0002"), ("oss", "head")]),
        ("ext0002", [("oss", "head")]),
    ],
)
def test_run_migrations__extension_migrations(
    mocker: MockerFixture,
    engine: Engine,
    tmp_path: Path,
    applied: str | None,
    expected_upgrades: list[tuple[str, str]],
) -> None:
    """Each pending extension revision runs after the revision it was written against."""
    extension = _write_extension(path=tmp_path)
    _write_extension_revision(
        path=tmp_path, revision="ext0001", down_revision=None, oss_revision=_OSS_REVISION_2
    )
    _write_extension_revision(
        path=tmp_path, revision="ext0002", down_revision="ext0001", oss_revision=_OSS_REVISION_4
    )
    mocker.patch.object(db_migrations, "_alembic_version_table_exists", return_value=True)
    mocker.patch.object(db_migrations, "_get_applied_extension_revision", return_value=applied)
    mock_run_command = mocker.patch.object(db_migrations, "_run_alembic_command")

    db_migrations.run_migrations(
        engine=engine, engine_url=_POSTGRES_URL, extension_migrations=extension
    )

    upgrades = [
        (
            "ext"
            if call.kwargs["config"].get_main_option("script_location") == str(tmp_path)
            else "oss",
            call.kwargs["revision"],
        )
        for call in mock_run_command.call_args_list
    ]
    assert upgrades == expected_upgrades


def test_run_migrations__extension_revision_without_oss_revision(
    engine: Engine,
    tmp_path: Path,
) -> None:
    extension = _write_extension(path=tmp_path)
    _write_extension_revision(
        path=tmp_path, revision="ext0001", down_revision=None, oss_revision=None
    )

    with pytest.raises(
        RuntimeError, match=r"Extension revision ext0001 does not set oss_revision\."
    ):
        db_migrations.run_migrations(
            engine=engine, engine_url=_POSTGRES_URL, extension_migrations=extension
        )


def test_run_migrations__extension_revision_with_unknown_oss_revision(
    engine: Engine,
    tmp_path: Path,
) -> None:
    extension = _write_extension(path=tmp_path)
    _write_extension_revision(
        path=tmp_path, revision="ext0001", down_revision=None, oss_revision="ffffffffffff"
    )

    with pytest.raises(
        RuntimeError,
        match=r"Extension revision ext0001 sets oss_revision to 'ffffffffffff', "
        r"which is not a lightly_studio revision\.",
    ):
        db_migrations.run_migrations(
            engine=engine, engine_url=_POSTGRES_URL, extension_migrations=extension
        )


def test_run_migrations__unknown_applied_extension_revision(
    mocker: MockerFixture,
    engine: Engine,
    tmp_path: Path,
) -> None:
    extension = _write_extension(path=tmp_path)
    _write_extension_revision(
        path=tmp_path, revision="ext0001", down_revision=None, oss_revision=_OSS_REVISION_2
    )
    mocker.patch.object(db_migrations, "_get_applied_extension_revision", return_value="ext0009")

    with pytest.raises(
        RuntimeError,
        match=r"The database has extension revision ext0009, which the extension does not have\.",
    ):
        db_migrations.run_migrations(
            engine=engine, engine_url=_POSTGRES_URL, extension_migrations=extension
        )


def _write_extension(path: Path) -> ExtensionMigrations:
    """Write the env.py of a test extension and return its migrations."""
    (path / "versions").mkdir()
    (path / "env.py").write_text(_EXTENSION_ENV)
    return ExtensionMigrations(script_location=path, version_table_schema="ext")


def _write_extension_revision(
    path: Path,
    revision: str,
    down_revision: str | None,
    oss_revision: str | None,
) -> None:
    """Write an extension revision that records the applied lightly_studio revision."""
    oss_revision_line = "" if oss_revision is None else f"oss_revision = {oss_revision!r}\n"
    (path / "versions" / f"{revision}.py").write_text(
        "from alembic import op\n"
        f"revision = {revision!r}\n"
        f"down_revision = {down_revision!r}\n"
        "branch_labels = None\n"
        "depends_on = None\n"
        f"{oss_revision_line}"
        "def upgrade() -> None:\n"
        '    op.execute("CREATE TABLE IF NOT EXISTS ext.applied '
        '(id serial PRIMARY KEY, revision text, oss_revision text)")\n'
        '    op.execute("INSERT INTO ext.applied (revision, oss_revision) '
        f"SELECT '{revision}', version_num FROM public.alembic_version\")\n"
        "def downgrade() -> None:\n"
        "    pass\n"
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


def test_postgres_extension_migrations__fresh_database(
    postgres_url: str | None,
    tmp_path: Path,
) -> None:
    """A fresh database applies each extension revision after its oss_revision."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")
    _reset_postgres_database(engine_url=postgres_url)
    extension = _write_extension(path=tmp_path)
    _write_extension_revision(
        path=tmp_path, revision="ext0001", down_revision=None, oss_revision=_OSS_REVISION_2
    )
    _write_extension_revision(
        path=tmp_path, revision="ext0002", down_revision="ext0001", oss_revision=_OSS_REVISION_4
    )
    engine = create_engine(db_url.ensure_psycopg3_driver(engine_url=postgres_url))
    try:
        db_migrations.run_migrations(
            engine=engine, engine_url=postgres_url, extension_migrations=extension
        )

        assert _read_extension_state(engine=engine) == (
            [("ext0001", _OSS_REVISION_2), ("ext0002", _OSS_REVISION_4)],
            [db_migrations.get_head_revision()],
            ["ext0002"],
        )
    finally:
        _drop_extension_schema(engine=engine)
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_extension_migrations__upgraded_database(
    postgres_url: str | None,
    tmp_path: Path,
) -> None:
    """An upgraded database applies the revisions in the same order as a fresh one."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")
    _reset_postgres_database(engine_url=postgres_url)
    extension = _write_extension(path=tmp_path)
    _write_extension_revision(
        path=tmp_path, revision="ext0001", down_revision=None, oss_revision=_OSS_REVISION_2
    )
    engine = create_engine(db_url.ensure_psycopg3_driver(engine_url=postgres_url))
    try:
        # An older release left the database at revision 3 and ext0001.
        config = db_migrations.get_alembic_config(engine_url=postgres_url)
        db_migrations._upgrade_extension(
            engine=engine, engine_url=postgres_url, config=config, extension_migrations=extension
        )
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision=_OSS_REVISION_3
        )
        _write_extension_revision(
            path=tmp_path, revision="ext0002", down_revision="ext0001", oss_revision=_OSS_REVISION_4
        )

        db_migrations.run_migrations(
            engine=engine, engine_url=postgres_url, extension_migrations=extension
        )

        assert _read_extension_state(engine=engine) == (
            [("ext0001", _OSS_REVISION_2), ("ext0002", _OSS_REVISION_4)],
            [db_migrations.get_head_revision()],
            ["ext0002"],
        )
    finally:
        _drop_extension_schema(engine=engine)
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def _read_extension_state(
    engine: Engine,
) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """Return the applied extension revisions and the two version tables.

    Each extension revision is listed with the lightly_studio revision that was applied
    when it ran.
    """
    with engine.connect() as connection:
        applied = connection.execute(
            text("SELECT revision, oss_revision FROM ext.applied ORDER BY id")
        ).all()
        oss_versions = (
            connection.execute(text("SELECT version_num FROM public.alembic_version"))
            .scalars()
            .all()
        )
        extension_versions = (
            connection.execute(text("SELECT version_num FROM ext.alembic_version")).scalars().all()
        )
    return [tuple(row) for row in applied], list(oss_versions), list(extension_versions)


def _drop_extension_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS ext CASCADE"))


def test_postgres_check__ignores_tables_in_other_schemas(
    postgres_url: str | None,
) -> None:
    """Alembic check ignores a model table outside the default schema."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")
    _reset_postgres_database(engine_url=postgres_url)
    engine = create_engine(db_url.ensure_psycopg3_driver(engine_url=postgres_url))
    # The schema "other" does not exist. The table is only in the metadata.
    table = Table(
        "other_table", SQLModel.metadata, Column("id", Integer, primary_key=True), schema="other"
    )
    try:
        db_migrations.run_migrations(engine=engine, engine_url=postgres_url)
        config = db_migrations.get_alembic_config(engine_url=postgres_url)
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            # Raises AutogenerateDiffsDetected if autogenerate wants to add the table.
            command.check(config)
    finally:
        SQLModel.metadata.remove(table)
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_embedding_plot__upgrade_preserves_existing_cache(
    postgres_url: str | None,
) -> None:
    """Adding plot storage leaves the previous cache available to old readers."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")
    _reset_postgres_database(engine_url=postgres_url)
    engine = create_engine(db_url.ensure_psycopg3_driver(engine_url=postgres_url))
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    try:
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="e4c3c74ae338"
        )
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO two_dim_embeddings (hash, x, y) "
                    "VALUES ('123', ARRAY[1.0], ARRAY[2.0])"
                )
            )
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="a3e921f6d502"
        )
        assert db_migrations._get_inspector(engine=engine).has_table(table_name="embedding_plot")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT hash, x, y FROM two_dim_embeddings")).one() == (
                "123",
                [1.0],
                [2.0],
            )
            assert connection.execute(text("SELECT count(*) FROM embedding_plot")).scalar_one() == 0
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_unused_embedding_cache__upgrade_and_downgrade(
    postgres_url: str | None,
) -> None:
    """Remove only the obsolete cache and restore an empty table on downgrade."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")
    _reset_postgres_database(engine_url=postgres_url)
    engine = create_engine(db_url.ensure_psycopg3_driver(engine_url=postgres_url))
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    try:
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="a3e921f6d502"
        )
        with Session(engine) as session:
            collection = create_collection(session=session)
            model = create_embedding_model(
                session=session, collection_id=collection.collection_id, embedding_dimension=2
            )
            image = create_image(session=session, collection_id=collection.collection_id)
            sample_id, model_id = image.sample_id, model.embedding_model_id
            session.add(
                SampleEmbeddingTable(
                    sample_id=sample_id,
                    embedding_model_id=model_id,
                    embedding=np.array([1.0, 2.0], dtype=np.float32),
                )
            )
            session.commit()
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO two_dim_embeddings VALUES ('old', ARRAY[1.0], ARRAY[2.0])")
            )
            connection.execute(
                text(
                    "INSERT INTO embedding_plot VALUES (:collection, :model, false, :token, :data)"
                ),
                {"collection": uuid4(), "model": uuid4(), "token": uuid4(), "data": b"saved"},
            )
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="head"
        )
        assert not db_migrations._get_inspector(engine=engine).has_table("two_dim_embeddings")
        with Session(engine) as session:
            embedding = session.get(SampleEmbeddingTable, (sample_id, model_id))
            assert embedding is not None
            assert list(embedding.embedding) == [1.0, 2.0]
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT data FROM embedding_plot")).scalar_one() == b"saved"
            )
        config.attributes.pop("connection", None)
        command.check(config)
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.downgrade, revision="a3e921f6d502"
        )
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM two_dim_embeddings")).scalar_one()
                == 0
            )
            assert (
                connection.execute(text("SELECT data FROM embedding_plot")).scalar_one() == b"saved"
            )
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_polygon_annotation__upgrade_and_downgrade(
    postgres_url: str | None,
) -> None:
    """Store polygon parts as JSON and remove the polygon table on downgrade."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")
    _reset_postgres_database(engine_url=postgres_url)
    engine = create_engine(db_url.ensure_psycopg3_driver(engine_url=postgres_url))
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    polygons = [
        [[10.5, 20.0], [30.0, 20.0], [30.0, 40.25]],
        [[50.0, 50.0], [60.0, 50.0], [60.0, 60.0]],
    ]
    try:
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="head"
        )
        with Session(engine) as session:
            collection = create_collection(session=session)
            image = create_image(session=session, collection_id=collection.collection_id)
            label = create_annotation_label(
                session=session, root_collection_id=collection.collection_id
            )
            annotation_sample = SampleTable(collection_id=collection.collection_id)
            session.add(annotation_sample)
            session.flush()
            session.add(
                AnnotationBaseTable(
                    sample_id=annotation_sample.sample_id,
                    annotation_type=AnnotationType.POLYGON,
                    annotation_label_id=label.annotation_label_id,
                    parent_sample_id=image.sample_id,
                )
            )
            session.flush()
            session.add(
                PolygonAnnotationTable(
                    sample_id=annotation_sample.sample_id,
                    x=10,
                    y=20,
                    width=50,
                    height=40,
                    polygons=polygons,
                )
            )
            session.commit()
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT polygons FROM polygon_annotation")
            ).scalar_one() == [
                [[10.5, 20.0], [30.0, 20.0], [30.0, 40.25]],
                [[50.0, 50.0], [60.0, 50.0], [60.0, 60.0]],
            ]
        config.attributes.pop("connection", None)
        command.check(config)
        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.downgrade, revision="1e2ff606de9f"
        )
        assert not db_migrations._get_inspector(engine=engine).has_table(
            table_name="polygon_annotation"
        )
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM annotation_base")).scalar_one() == 0
            )
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


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


def test_postgres_tag_name_uniqueness__consolidates_cross_kind_duplicates(
    postgres_url: str | None,
) -> None:
    """Cross-kind duplicate tags and their links are merged during migration."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    collection_id = "00000000-0000-0000-0000-000000000002"
    sample_tag_id = "00000000-0000-0000-0000-000000000003"
    annotation_tag_id = "00000000-0000-0000-0000-000000000004"
    first_sample_id = "00000000-0000-0000-0000-000000000005"
    second_sample_id = "00000000-0000-0000-0000-000000000006"

    try:
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="b8c9d0e1f2a3",
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
                    INSERT INTO sample (sample_id, collection_id, created_at, updated_at)
                    VALUES
                        (:first_sample_id, :collection_id, NOW(), NOW()),
                        (:second_sample_id, :collection_id, NOW(), NOW())
                    """
                ),
                parameters={
                    "collection_id": collection_id,
                    "first_sample_id": first_sample_id,
                    "second_sample_id": second_sample_id,
                },
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO tag (
                        name, kind, tag_id, collection_id, created_at, updated_at
                    ) VALUES
                        (
                            'duplicate', 'annotation', :annotation_tag_id,
                            :collection_id, NOW(), NOW()
                        ),
                        ('duplicate', 'sample', :sample_tag_id, :collection_id, NOW(), NOW())
                    """
                ),
                parameters={
                    "annotation_tag_id": annotation_tag_id,
                    "collection_id": collection_id,
                    "sample_tag_id": sample_tag_id,
                },
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO sampletaglinktable (sample_id, tag_id)
                    VALUES
                        (:first_sample_id, :annotation_tag_id),
                        (:first_sample_id, :sample_tag_id),
                        (:second_sample_id, :annotation_tag_id)
                    """
                ),
                parameters={
                    "annotation_tag_id": annotation_tag_id,
                    "first_sample_id": first_sample_id,
                    "sample_tag_id": sample_tag_id,
                    "second_sample_id": second_sample_id,
                },
            )

        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="head"
        )

        with engine.connect() as connection:
            tags = connection.execute(
                statement=text("SELECT tag_id FROM tag WHERE name = 'duplicate'")
            ).all()
            links = connection.execute(
                statement=text(
                    "SELECT sample_id, tag_id FROM sampletaglinktable ORDER BY sample_id"
                )
            ).all()
        assert [str(tag_id) for (tag_id,) in tags] == [sample_tag_id]
        assert [(str(sample_id), str(tag_id)) for sample_id, tag_id in links] == [
            (first_sample_id, sample_tag_id),
            (second_sample_id, sample_tag_id),
        ]

        config.attributes.pop("connection", None)
        command.check(config)
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_tag_links__moved_to_sample_collection(
    postgres_url: str | None,
) -> None:
    """A tag link whose sample is in another collection moves to a tag in that collection."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    image_collection_id = "00000000-0000-0000-0000-000000000002"
    gt_collection_id = "00000000-0000-0000-0000-000000000003"
    pred_collection_id = "00000000-0000-0000-0000-000000000004"
    image_id = "00000000-0000-0000-0000-000000000005"
    gt_annotation_id = "00000000-0000-0000-0000-000000000006"
    pred_annotation_id = "00000000-0000-0000-0000-000000000007"
    review_tag_id = "00000000-0000-0000-0000-000000000008"
    qa_tag_id = "00000000-0000-0000-0000-000000000009"
    empty_tag_id = "00000000-0000-0000-0000-000000000010"
    pred_review_tag_id = "00000000-0000-0000-0000-000000000011"

    try:
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="8cb37a9d104e",
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
                        name, sample_type, collection_id, parent_collection_id, dataset_id,
                        created_at, updated_at
                    ) VALUES
                        ('images', 'IMAGE', :image_collection_id, NULL, :dataset_id,
                         NOW(), NOW()),
                        ('ground_truth', 'ANNOTATION', :gt_collection_id, :image_collection_id,
                         :dataset_id, NOW(), NOW()),
                        ('predictions', 'ANNOTATION', :pred_collection_id, :image_collection_id,
                         :dataset_id, NOW(), NOW())
                    """
                ),
                parameters={
                    "dataset_id": dataset_id,
                    "image_collection_id": image_collection_id,
                    "gt_collection_id": gt_collection_id,
                    "pred_collection_id": pred_collection_id,
                },
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO sample (sample_id, collection_id, created_at, updated_at)
                    VALUES
                        (:image_id, :image_collection_id, NOW(), NOW()),
                        (:gt_annotation_id, :gt_collection_id, NOW(), NOW()),
                        (:pred_annotation_id, :pred_collection_id, NOW(), NOW())
                    """
                ),
                parameters={
                    "image_id": image_id,
                    "gt_annotation_id": gt_annotation_id,
                    "pred_annotation_id": pred_annotation_id,
                    "image_collection_id": image_collection_id,
                    "gt_collection_id": gt_collection_id,
                    "pred_collection_id": pred_collection_id,
                },
            )
            # "review" holds annotations of both sources. "qa" holds the image and a ground
            # truth annotation. The predictions collection already has a "review" tag.
            connection.execute(
                statement=text(
                    """
                    INSERT INTO tag (name, kind, tag_id, collection_id, created_at, updated_at)
                    VALUES
                        ('review', 'annotation', :review_tag_id, :image_collection_id,
                         NOW(), NOW()),
                        ('qa', 'sample', :qa_tag_id, :image_collection_id, NOW(), NOW()),
                        ('empty', 'sample', :empty_tag_id, :image_collection_id, NOW(), NOW()),
                        ('review', 'annotation', :pred_review_tag_id, :pred_collection_id,
                         NOW(), NOW())
                    """
                ),
                parameters={
                    "review_tag_id": review_tag_id,
                    "qa_tag_id": qa_tag_id,
                    "empty_tag_id": empty_tag_id,
                    "pred_review_tag_id": pred_review_tag_id,
                    "image_collection_id": image_collection_id,
                    "pred_collection_id": pred_collection_id,
                },
            )
            connection.execute(
                statement=text(
                    """
                    INSERT INTO sampletaglinktable (sample_id, tag_id)
                    VALUES
                        (:gt_annotation_id, :review_tag_id),
                        (:pred_annotation_id, :review_tag_id),
                        (:image_id, :qa_tag_id),
                        (:gt_annotation_id, :qa_tag_id)
                    """
                ),
                parameters={
                    "image_id": image_id,
                    "gt_annotation_id": gt_annotation_id,
                    "pred_annotation_id": pred_annotation_id,
                    "review_tag_id": review_tag_id,
                    "qa_tag_id": qa_tag_id,
                },
            )

        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="68fcd3378db6"
        )

        with engine.connect() as connection:
            tags = connection.execute(
                statement=text(
                    "SELECT collection_id, name, kind FROM tag ORDER BY collection_id, name"
                )
            ).all()
            links = connection.execute(
                statement=text(
                    """
                    SELECT link.sample_id, tag.collection_id, tag.name
                    FROM sampletaglinktable AS link
                    JOIN tag ON tag.tag_id = link.tag_id
                    ORDER BY link.sample_id, tag.name
                    """
                )
            ).all()
            pred_review_tag_ids = connection.execute(
                statement=text("SELECT tag_id FROM tag WHERE collection_id = :pred_collection_id"),
                parameters={"pred_collection_id": pred_collection_id},
            ).all()
        assert [(str(collection_id), name, kind) for collection_id, name, kind in tags] == [
            (image_collection_id, "empty", "sample"),
            (image_collection_id, "qa", "sample"),
            (gt_collection_id, "qa", "annotation"),
            (gt_collection_id, "review", "annotation"),
            (pred_collection_id, "review", "annotation"),
        ]
        assert [
            (str(sample_id), str(collection_id), name) for sample_id, collection_id, name in links
        ] == [
            (image_id, image_collection_id, "qa"),
            (gt_annotation_id, gt_collection_id, "qa"),
            (gt_annotation_id, gt_collection_id, "review"),
            (pred_annotation_id, pred_collection_id, "review"),
        ]
        assert [str(tag_id) for (tag_id,) in pred_review_tag_ids] == [pred_review_tag_id]

        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="head"
        )
        config.attributes.pop("connection", None)
        command.check(config)
    finally:
        _restore_shared_database_to_head(engine=engine, engine_url=postgres_url)
        engine.dispose()


def test_postgres_tag_kind__dropped_and_restored(
    postgres_url: str | None,
) -> None:
    """The migration drops the tag kind and the downgrade restores it from the collection."""
    if postgres_url is None:
        pytest.skip("Requires --postgres")

    _reset_postgres_database(engine_url=postgres_url)
    normalized_url = db_url.ensure_psycopg3_driver(engine_url=postgres_url)
    engine = create_engine(normalized_url)
    config = db_migrations.get_alembic_config(engine_url=postgres_url)
    dataset_id = "00000000-0000-0000-0000-000000000001"
    image_collection_id = "00000000-0000-0000-0000-000000000002"
    gt_collection_id = "00000000-0000-0000-0000-000000000003"
    image_tag_id = "00000000-0000-0000-0000-000000000004"
    gt_tag_id = "00000000-0000-0000-0000-000000000005"
    orphan_tag_id = "00000000-0000-0000-0000-000000000006"
    deleted_collection_id = "00000000-0000-0000-0000-000000000007"

    try:
        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.upgrade,
            revision="68fcd3378db6",
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
                        name, sample_type, collection_id, parent_collection_id, dataset_id,
                        created_at, updated_at
                    ) VALUES
                        ('images', 'IMAGE', :image_collection_id, NULL, :dataset_id,
                         NOW(), NOW()),
                        ('ground_truth', 'ANNOTATION', :gt_collection_id, :image_collection_id,
                         :dataset_id, NOW(), NOW())
                    """
                ),
                parameters={
                    "dataset_id": dataset_id,
                    "image_collection_id": image_collection_id,
                    "gt_collection_id": gt_collection_id,
                },
            )
            # The ground truth tag has no samples, so only its collection gives its kind.
            # The collection of the orphaned tag was deleted.
            connection.execute(
                statement=text(
                    """
                    INSERT INTO tag (name, kind, tag_id, collection_id, created_at, updated_at)
                    VALUES
                        ('selected', 'sample', :image_tag_id, :image_collection_id,
                         NOW(), NOW()),
                        ('reviewed', 'annotation', :gt_tag_id, :gt_collection_id,
                         NOW(), NOW()),
                        ('orphaned', 'annotation', :orphan_tag_id, :deleted_collection_id,
                         NOW(), NOW())
                    """
                ),
                parameters={
                    "image_tag_id": image_tag_id,
                    "gt_tag_id": gt_tag_id,
                    "orphan_tag_id": orphan_tag_id,
                    "image_collection_id": image_collection_id,
                    "gt_collection_id": gt_collection_id,
                    "deleted_collection_id": deleted_collection_id,
                },
            )

        db_migrations._run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision="head"
        )
        columns = db_migrations._get_inspector(engine=engine).get_columns(table_name="tag")
        assert "kind" not in {column["name"] for column in columns}
        with engine.connect() as connection:
            tag_ids = connection.execute(
                statement=text("SELECT tag_id FROM tag ORDER BY tag_id")
            ).all()
        assert [str(tag_id) for (tag_id,) in tag_ids] == [
            image_tag_id,
            gt_tag_id,
            orphan_tag_id,
        ]

        config.attributes.pop("connection", None)
        command.check(config)

        db_migrations._run_alembic_command(
            engine=engine,
            config=config,
            fn=command.downgrade,
            revision="68fcd3378db6",
        )
        columns = db_migrations._get_inspector(engine=engine).get_columns(table_name="tag")
        kind_column = next(column for column in columns if column["name"] == "kind")
        assert kind_column["nullable"] is False
        with engine.connect() as connection:
            tags = connection.execute(
                statement=text("SELECT tag_id, kind FROM tag ORDER BY tag_id")
            ).all()
        assert [(str(tag_id), kind) for tag_id, kind in tags] == [
            (image_tag_id, "sample"),
            (gt_tag_id, "annotation"),
            (orphan_tag_id, "sample"),
        ]
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
