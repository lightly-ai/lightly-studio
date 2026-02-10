"""Tests for dialect-aware JSON extraction helpers."""

from pytest_mock import MockerFixture

from lightly_studio import db_manager
from lightly_studio.db_manager import DatabaseBackend
from lightly_studio.resolvers.metadata_resolver.json_utils import (
    METADATA_COLUMN,
    _build_pg_json_accessor,
    json_extract_sql,
    json_not_null_sql,
)


class TestBuildPgJsonAccessor:
    """Tests for the Postgres JSON accessor builder."""

    def test_simple_key(self) -> None:
        result = _build_pg_json_accessor("metadata.data", "temperature")
        assert result == "metadata.data->>'temperature'"

    def test_nested_key(self) -> None:
        result = _build_pg_json_accessor("metadata.data", "test_dict.int_key")
        assert result == "metadata.data->'test_dict'->>'int_key'"

    def test_deeply_nested_key(self) -> None:
        result = _build_pg_json_accessor("metadata.data", "a.b.c")
        assert result == "metadata.data->'a'->'b'->>'c'"

    def test_array_index(self) -> None:
        result = _build_pg_json_accessor("metadata.data", "test_dict.nested_list[0]")
        assert result == "metadata.data->'test_dict'->'nested_list'->>0"

    def test_cast_to_float(self) -> None:
        result = _build_pg_json_accessor("metadata.data", "temperature", cast_to_float=True)
        assert result == "(metadata.data->>'temperature')::float"

    def test_nested_cast_to_float(self) -> None:
        result = _build_pg_json_accessor("metadata.data", "test_dict.int_key", cast_to_float=True)
        assert result == "(metadata.data->'test_dict'->>'int_key')::float"

    def test_custom_column(self) -> None:
        result = _build_pg_json_accessor("my_table.json_col", "key")
        assert result == "my_table.json_col->>'key'"


class TestJsonExtractSqlDuckDB:
    """Tests for json_extract_sql with the DuckDB backend."""

    def test_simple_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.DUCKDB)
        result = json_extract_sql("temperature")
        assert result == f"json_extract({METADATA_COLUMN}, '$.temperature')"

    def test_nested_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.DUCKDB)
        result = json_extract_sql("test_dict.int_key")
        assert result == f"json_extract({METADATA_COLUMN}, '$.test_dict.int_key')"

    def test_cast_to_float(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.DUCKDB)
        result = json_extract_sql("temperature", cast_to_float=True)
        assert result == f"CAST(json_extract({METADATA_COLUMN}, '$.temperature') AS FLOAT)"

    def test_custom_column(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.DUCKDB)
        result = json_extract_sql("key", column="other.col")
        assert result == "json_extract(other.col, '$.key')"


class TestJsonExtractSqlPostgres:
    """Tests for json_extract_sql with the Postgres backend."""

    def test_simple_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_extract_sql("temperature")
        assert result == f"{METADATA_COLUMN}->>'temperature'"

    def test_nested_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_extract_sql("test_dict.int_key")
        assert result == f"{METADATA_COLUMN}->'test_dict'->>'int_key'"

    def test_cast_to_float(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_extract_sql("temperature", cast_to_float=True)
        assert result == f"({METADATA_COLUMN}->>'temperature')::float"

    def test_nested_cast_to_float(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_extract_sql("test_dict.int_key", cast_to_float=True)
        assert result == f"({METADATA_COLUMN}->'test_dict'->>'int_key')::float"

    def test_array_index(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_extract_sql("test_dict.nested_list[0]")
        assert result == f"{METADATA_COLUMN}->'test_dict'->'nested_list'->>0"


class TestJsonNotNullSqlDuckDB:
    """Tests for json_not_null_sql with the DuckDB backend."""

    def test_simple_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.DUCKDB)
        result = json_not_null_sql("temperature")
        assert result == f"json_extract({METADATA_COLUMN}, '$.temperature') IS NOT NULL"

    def test_nested_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.DUCKDB)
        result = json_not_null_sql("test_dict.int_key")
        assert result == f"json_extract({METADATA_COLUMN}, '$.test_dict.int_key') IS NOT NULL"


class TestJsonNotNullSqlPostgres:
    """Tests for json_not_null_sql with the Postgres backend."""

    def test_simple_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_not_null_sql("temperature")
        assert result == f"{METADATA_COLUMN}->>'temperature' IS NOT NULL"

    def test_nested_key(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_not_null_sql("test_dict.int_key")
        assert result == f"{METADATA_COLUMN}->'test_dict'->>'int_key' IS NOT NULL"

    def test_custom_column(self, mocker: MockerFixture) -> None:
        mocker.patch.object(db_manager, "get_backend", return_value=DatabaseBackend.POSTGRESQL)
        result = json_not_null_sql("key", column="other.col")
        assert result == "other.col->>'key' IS NOT NULL"
