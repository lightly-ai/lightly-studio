"""Tests for the schema_compat row."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.database import db_migrations, schema_compat
from lightly_studio.errors import SchemaCompatError
from lightly_studio.models.schema_compat import SchemaCompatTable


def _engine(tmp_path: Path) -> Engine:
    engine = create_engine(f"duckdb:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(bind=engine)
    return engine


def test_write_schema_compat__inserts_row(tmp_path: Path) -> None:
    engine = _engine(tmp_path=tmp_path)

    with engine.begin() as connection:
        schema_compat.write_schema_compat(connection=connection, oss_revision="abc123")

    row = schema_compat.read_schema_compat(engine=engine)
    assert row is not None
    assert row.oss_revision == "abc123"
    assert row.min_client_version == schema_compat.MIN_SUPPORTED_CLIENT_VERSION


def test_write_schema_compat__replaces_row(tmp_path: Path) -> None:
    engine = _engine(tmp_path=tmp_path)
    with engine.begin() as connection:
        schema_compat.write_schema_compat(connection=connection, oss_revision="abc123")

    with engine.begin() as connection:
        schema_compat.write_schema_compat(connection=connection, oss_revision="def456")

    row = schema_compat.read_schema_compat(engine=engine)
    assert row is not None
    assert row.oss_revision == "def456"


def test_read_schema_compat__no_row(tmp_path: Path) -> None:
    engine = _engine(tmp_path=tmp_path)

    assert schema_compat.read_schema_compat(engine=engine) is None


# Revisions of the migrations package: the head, one of its ancestors and an unknown id.
_HEAD = "7b4e2f1b1a31"
_ANCESTOR = "8660d246e98e"
_UNKNOWN = "ffffffffffff"


def _row(oss_revision: str, min_client_version: str = "1.0.0") -> SchemaCompatTable:
    return SchemaCompatTable(oss_revision=oss_revision, min_client_version=min_client_version)


def test_check_client_compatibility__same_revision() -> None:
    script = db_migrations.get_script_directory()
    assert script.get_current_head() == _HEAD

    schema_compat.check_client_compatibility(
        row=_row(oss_revision=_HEAD), client_version="1.0.0", script=script
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
            row=_row(oss_revision=_ANCESTOR),
            client_version="1.0.0",
            script=db_migrations.get_script_directory(),
        )


def test_check_client_compatibility__unknown_revision() -> None:
    schema_compat.check_client_compatibility(
        row=_row(oss_revision=_UNKNOWN),
        client_version="1.0.0",
        script=db_migrations.get_script_directory(),
    )
