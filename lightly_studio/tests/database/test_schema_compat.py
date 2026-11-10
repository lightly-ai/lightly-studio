"""Tests for the schema_compat row."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.database import schema_compat


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
