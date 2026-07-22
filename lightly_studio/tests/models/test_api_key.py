"""Tests for API key models."""

from sqlalchemy import DateTime, Enum, Integer, UniqueConstraint
from sqlmodel import SQLModel

from lightly_studio.models.api_key import ApiKeyTable


def test_api_key_table_column_types() -> None:
    """Columns use the types expected by the PostgreSQL migration."""
    table = SQLModel.metadata.tables[ApiKeyTable.__tablename__]

    assert isinstance(table.c.user_id.type, Integer)

    status_type = table.c.status.type
    assert isinstance(status_type, Enum)
    assert status_type.enums == ["ACTIVE", "REVOKED"]

    for column_name in ("created_at", "expires_at", "last_used_at"):
        date_type = table.c[column_name].type
        assert isinstance(date_type, DateTime)
        assert date_type.timezone


def test_api_key_hash_has_one_unique_index() -> None:
    """The key hash is enforced by one unique index."""
    table = SQLModel.metadata.tables[ApiKeyTable.__tablename__]

    key_hash_indexes = [index for index in table.indexes if index.columns.keys() == ["key_hash"]]
    assert len(key_hash_indexes) == 1
    assert key_hash_indexes[0].unique
    assert not any(isinstance(constraint, UniqueConstraint) for constraint in table.constraints)
