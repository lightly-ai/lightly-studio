"""Tests for API key models."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import DateTime, Enum, Integer, UniqueConstraint
from sqlmodel import SQLModel

from lightly_studio.models.api_key import ApiKeyCreate, ApiKeyTable


class TestApiKeyCreate:
    """Tests for the API key creation model."""

    def test_expires_at__none(self) -> None:
        api_key = ApiKeyCreate(name="Automation key", user_id=42)

        assert api_key.expires_at is None

    def test_expires_at__naive(self) -> None:
        expires_at = datetime(2027, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None)

        with pytest.raises(ValidationError, match="must include timezone information"):
            ApiKeyCreate(name="Automation key", user_id=42, expires_at=expires_at)

    def test_expires_at__aware(self) -> None:
        expires_at = datetime(2027, 1, 1, 2, tzinfo=timezone(timedelta(hours=2)))

        api_key = ApiKeyCreate(name="Automation key", user_id=42, expires_at=expires_at)

        assert api_key.expires_at == datetime(2027, 1, 1, tzinfo=timezone.utc)
        assert api_key.expires_at.tzinfo is timezone.utc


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
