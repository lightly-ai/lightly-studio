from __future__ import annotations

from importlib import metadata
from pathlib import Path

import pytest
from sqlmodel import select

from lightly_studio import db_manager
from lightly_studio.models.database_version import DatabaseVersionTable

PACKAGE_VERSION = metadata.version("lightly-studio")


def _create_database(db_url: str, version: str | None) -> None:
    db_manager.connect(db_url=db_url)
    with db_manager.session() as session:
        db_version = session.exec(select(DatabaseVersionTable)).first()
        assert db_version is not None
        if version != db_version.version:
            session.delete(db_version)
            if version is not None:
                session.add(DatabaseVersionTable(version=version))
    db_manager.close()


def _drop_database_version_table(db_url: str) -> None:
    _create_database(db_url=db_url, version=PACKAGE_VERSION)
    db_manager.connect(db_url=db_url)
    with db_manager.session() as session:
        session.connection().exec_driver_sql("DROP TABLE database_version")
    db_manager.close()


@pytest.mark.usefixtures("patch_engine_singleton")
class TestValidateOrInitializeDatabaseVersion:
    """Tests for `_validate_or_initialize_database_version`.

    Covered cases:
    1. Fresh database with no managed tables: insert the expected version.
    2. Existing database without a `database_version` table: warn.
    3a. Existing database with a `database_version` table but 0 rows: raise.
    3b. Existing database with a `database_version` table but >1 rows: raise.
    3c. Existing database with 1 row and a different version: warn.
    3d. Existing database with 1 row and the expected version: do nothing.
    """

    def test_connect__case_1__fresh_database_initializes_expected_version(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db_url = f"duckdb:///{tmp_path / 'no_db.db'}"
        caplog.clear()
        with caplog.at_level("WARNING"):
            db_manager.connect(db_url=db_url, must_exist=False)
        assert caplog.messages == []
        with db_manager.session() as session:
            assert session.exec(select(DatabaseVersionTable.version)).first() == PACKAGE_VERSION
        db_manager.close()

    def test_connect__case_2__existing_database_without_database_version_table_warns(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db_url = f"duckdb:///{tmp_path / 'db_without_version.db'}"
        _drop_database_version_table(db_url=db_url)
        expected_warning = (
            f"Incompatible database schema version. Expected version "
            f"'{PACKAGE_VERSION}', but found missing version metadata."
        )
        caplog.clear()
        with caplog.at_level("WARNING"):
            db_manager.connect(db_url=db_url, must_exist=True)
        assert caplog.messages == [expected_warning]
        with db_manager.session() as session:
            assert session.exec(select(DatabaseVersionTable.version)).first() is None
        db_manager.close()

    def test_connect__case_3a__database_version_table_without_rows_raises(
        self,
        tmp_path: Path,
    ) -> None:
        db_url = f"duckdb:///{tmp_path / 'empty_database_version.db'}"
        _create_database(db_url=db_url, version=None)

        with pytest.raises(
            RuntimeError,
            match=(
                r"Expected exactly one row in 'database_version' when the table already "
                r"exists, got 0."
            ),
        ):
            db_manager.connect(db_url=db_url, must_exist=True)

    def test_connect__case_3b__database_version_table_with_multiple_rows_raises(
        self,
        tmp_path: Path,
    ) -> None:
        db_url = f"duckdb:///{tmp_path / 'db_with_multiple_versions.db'}"
        _create_database(db_url=db_url, version=PACKAGE_VERSION)

        db_manager.connect(db_url=db_url)
        with db_manager.session() as session:
            session.add(DatabaseVersionTable(version="0.0.0"))
        db_manager.close()

        with pytest.raises(
            RuntimeError,
            match=(
                r"Expected at most one row in 'database_version' when the table already "
                r"exists, got 2."
            ),
        ):
            db_manager.connect(db_url=db_url, must_exist=True)

    def test_connect__case_3c__database_version_mismatch_warns(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db_url = f"duckdb:///{tmp_path / 'db_with_other_version.db'}"
        _create_database(db_url=db_url, version="0.0.0")
        expected_warning = (
            f"Incompatible database schema version. Expected version '{PACKAGE_VERSION}', "
            "got '0.0.0'."
        )
        caplog.clear()
        with caplog.at_level("WARNING"):
            db_manager.connect(db_url=db_url, must_exist=True)
        assert caplog.messages == [expected_warning]
        with db_manager.session() as session:
            assert session.exec(select(DatabaseVersionTable.version)).first() == "0.0.0"
        db_manager.close()

    def test_connect__case_3d__database_version_match_does_nothing(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        db_url = f"duckdb:///{tmp_path / 'db_with_same_version.db'}"
        _create_database(db_url=db_url, version=PACKAGE_VERSION)
        caplog.clear()
        with caplog.at_level("WARNING"):
            db_manager.connect(db_url=db_url, must_exist=True)
        assert caplog.messages == []
        with db_manager.session() as session:
            assert session.exec(select(DatabaseVersionTable.version)).first() == PACKAGE_VERSION
        db_manager.close()
