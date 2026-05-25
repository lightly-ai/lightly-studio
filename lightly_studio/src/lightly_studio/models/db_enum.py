"""Helpers for persisting ``str, Enum`` types as native database enum types."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def enum_values(enum_cls: type[E]) -> list[str]:
    """Return persisted string values for a str enum class."""
    return [member.value for member in enum_cls]


def enum_type_name(enum_cls: type[E]) -> str:
    """Return the PostgreSQL enum type name for a str enum class."""
    return enum_cls.__name__.lower()


def enum_column(enum_cls: type[E], nullable: bool = False) -> Column[Any]:
    """SQLAlchemy column that stores str enum members by ``.value`` in a DB enum type."""
    return Column(
        SAEnum(
            enum_cls,
            native_enum=True,
            values_callable=enum_values,
            name=enum_type_name(enum_cls),
        ),
        nullable=nullable,
    )
