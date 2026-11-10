"""Tests for the schema_compat row."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.database import db_migrations, schema_compat
from lightly_studio.errors import SchemaCompatError
from lightly_studio.models.schema_compat import SchemaCompatTable

# Revisions of the migrations package: the head, one of its ancestors and an unknown id.
_HEAD = "7b4e2f1b1a31"
_ANCESTOR = "8660d246e98e"
_UNKNOWN = "ffffffffffff"


def test_on_version_apply__updates_oss_revision(tmp_path: Path, mocker: MockerFixture) -> None:
    engine = _create_engine_with_tables(tmp_path=tmp_path)
    _insert_row(engine=engine, oss_revision="abc123", min_client_version="1.0")

    _apply(engine=engine, mocker=mocker, is_upgrade=True, module_attributes={}, heads={"def456"})

    row = schema_compat.read_schema_compat(engine=engine)
    assert row is not None
    assert (row.oss_revision, row.min_client_version) == ("def456", "1.0")


def test_on_version_apply__writes_declared_min_client_version(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    engine = _create_engine_with_tables(tmp_path=tmp_path)
    _insert_row(engine=engine, oss_revision="abc123", min_client_version="1.0")

    _apply(
        engine=engine,
        mocker=mocker,
        is_upgrade=True,
        module_attributes={"min_client_version": "1.9"},
        heads={"def456"},
    )

    row = schema_compat.read_schema_compat(engine=engine)
    assert row is not None
    assert (row.oss_revision, row.min_client_version) == ("def456", "1.9")


def test_on_version_apply__downgrade_keeps_min_client_version(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    engine = _create_engine_with_tables(tmp_path=tmp_path)
    _insert_row(engine=engine, oss_revision="abc123", min_client_version="1.0")

    _apply(
        engine=engine,
        mocker=mocker,
        is_upgrade=False,
        module_attributes={"min_client_version": "1.9"},
        heads={"def456"},
    )

    row = schema_compat.read_schema_compat(engine=engine)
    assert row is not None
    assert (row.oss_revision, row.min_client_version) == ("def456", "1.0")


def test_on_version_apply__no_table(tmp_path: Path, mocker: MockerFixture) -> None:
    # Before the revision that creates the table, the hook does nothing.
    engine = create_engine(f"duckdb:///{tmp_path / 'test.db'}")

    _apply(
        engine=engine,
        mocker=mocker,
        is_upgrade=True,
        module_attributes={"min_client_version": "1.9"},
        heads={"def456"},
    )

    assert schema_compat.read_schema_compat(engine=engine) is None


def test_on_version_apply__offline_mode(mocker: MockerFixture) -> None:
    # Offline mode has a mock connection that cannot be inspected.
    ctx = mocker.MagicMock(as_sql=True)

    schema_compat.on_version_apply(ctx=ctx, step=mocker.MagicMock(), heads={"def456"}, run_args={})

    ctx.connection.execute.assert_not_called()


def test_read_schema_compat__no_row(tmp_path: Path) -> None:
    engine = _create_engine_with_tables(tmp_path=tmp_path)

    assert schema_compat.read_schema_compat(engine=engine) is None


def test_read_schema_compat__no_table(tmp_path: Path) -> None:
    engine = create_engine(f"duckdb:///{tmp_path / 'test.db'}")

    assert schema_compat.read_schema_compat(engine=engine) is None


def test_check_client_compatibility__same_revision() -> None:
    script = db_migrations.get_script_directory()
    assert script.get_current_head() == _HEAD

    schema_compat.check_client_compatibility(
        row=_row(oss_revision=_HEAD, min_client_version="1.0.0"),
        client_version="1.0.0",
        script=script,
    )


def test_check_client_compatibility__no_row() -> None:
    with pytest.raises(SchemaCompatError, match=r"Upgrade the server first\."):
        schema_compat.check_client_compatibility(
            row=None, client_version="1.0.0", script=db_migrations.get_script_directory()
        )


def test_check_client_compatibility__client_too_old() -> None:
    with pytest.raises(
        SchemaCompatError,
        match=r"The database needs lightly-studio >= 1\.9, this client is 1\.7\.",
    ):
        schema_compat.check_client_compatibility(
            row=_row(oss_revision=_HEAD, min_client_version="1.9"),
            client_version="1.7",
            script=db_migrations.get_script_directory(),
        )


def test_check_client_compatibility__database_behind() -> None:
    with pytest.raises(SchemaCompatError, match=r"Upgrade the server first\."):
        schema_compat.check_client_compatibility(
            row=_row(oss_revision=_ANCESTOR, min_client_version="1.0.0"),
            client_version="1.0.0",
            script=db_migrations.get_script_directory(),
        )


def test_check_client_compatibility__unknown_revision() -> None:
    schema_compat.check_client_compatibility(
        row=_row(oss_revision=_UNKNOWN, min_client_version="1.0.0"),
        client_version="1.0.0",
        script=db_migrations.get_script_directory(),
    )


def _create_engine_with_tables(tmp_path: Path) -> Engine:
    engine = create_engine(f"duckdb:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(bind=engine)
    return engine


def _insert_row(engine: Engine, oss_revision: str, min_client_version: str) -> None:
    with Session(engine) as session:
        session.add(
            SchemaCompatTable(
                id=1, oss_revision=oss_revision, min_client_version=min_client_version
            )
        )
        session.commit()


def _apply(
    engine: Engine,
    mocker: MockerFixture,
    is_upgrade: bool,
    module_attributes: Mapping[str, str],
    heads: set[str],
) -> None:
    step = mocker.MagicMock(is_upgrade=is_upgrade)
    step.up_revision.module = SimpleNamespace(**module_attributes)
    with engine.begin() as connection:
        schema_compat.on_version_apply(
            ctx=mocker.MagicMock(as_sql=False, connection=connection),
            step=step,
            heads=heads,
            run_args={},
        )


def _row(oss_revision: str, min_client_version: str) -> SchemaCompatTable:
    return SchemaCompatTable(oss_revision=oss_revision, min_client_version=min_client_version)
