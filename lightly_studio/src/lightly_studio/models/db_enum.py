"""Helpers for persisting ``str, Enum`` types as VARCHAR values in the database."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def enum_values(enum_cls: type[E]) -> list[str]:
    """Return persisted string values for a str enum class."""
    return [member.value for member in enum_cls]


def enum_value_max_length(enum_cls: type[E]) -> int:
    """Return the length of the longest enum value string."""
    return max(len(member.value) for member in enum_cls)


def str_enum_column(enum_cls: type[E], *, nullable: bool = False) -> Column[Any]:
    """SQLAlchemy column that stores str enum members by ``.value`` in VARCHAR."""
    return Column(
        SAEnum(
            enum_cls,
            native_enum=False,
            values_callable=enum_values,
            length=enum_value_max_length(enum_cls),
        ),
        nullable=nullable,
    )
