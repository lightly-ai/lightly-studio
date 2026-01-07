"""Base field classes for building dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar, Union

from sqlalchemy.orm import Mapped

from lightly_studio.core.dataset_query.field_expression import (
    ComparableFieldExpression,
    OrdinalFieldExpression,
)

T = TypeVar("T")


class Field(ABC):
    """Abstract base class for all field types in dataset queries."""

    @abstractmethod
    def get_sqlmodel_field(self) -> Mapped[Any]:
        """Get the database column or property that this field represents.

        Returns:
            The database column or property for queries.
        """


class OrdinalField(Field, Generic[T]):
    """Generic field for ordinal values that support comparison operations.

    Ordinal values have a natural ordering and support all comparison operators:
    >, <, >=, <=, ==, !=
    """

    def __init__(self, column: Mapped[T]) -> None:
        """Initialize the ordinal field with a database column.

        Args:
            column: The database column this field represents.
        """
        self._column = column

    def get_sqlmodel_field(self) -> Mapped[T]:
        """Get the ordinal database column or property.

        Returns:
            The ordinal column for database queries.
        """
        return self._column

    def __gt__(self, other: T) -> OrdinalFieldExpression[T]:
        """Create a greater-than expression."""
        return OrdinalFieldExpression(field=self, operator=">", value=other)

    def __lt__(self, other: T) -> OrdinalFieldExpression[T]:
        """Create a less-than expression."""
        return OrdinalFieldExpression(field=self, operator="<", value=other)

    def __ge__(self, other: T) -> OrdinalFieldExpression[T]:
        """Create a greater-than-or-equal expression."""
        return OrdinalFieldExpression(field=self, operator=">=", value=other)

    def __le__(self, other: T) -> OrdinalFieldExpression[T]:
        """Create a less-than-or-equal expression."""
        return OrdinalFieldExpression(field=self, operator="<=", value=other)

    def __eq__(self, other: T) -> OrdinalFieldExpression[T]:  # type: ignore[override]
        """Create an equality expression."""
        return OrdinalFieldExpression(field=self, operator="==", value=other)

    def __ne__(self, other: T) -> OrdinalFieldExpression[T]:  # type: ignore[override]
        """Create a not-equal expression."""
        return OrdinalFieldExpression(field=self, operator="!=", value=other)


NumericalField = OrdinalField[Union[float, int]]
DatetimeField = OrdinalField[datetime]


class ComparableField(Field, Generic[T]):
    """Field for values that supports equality operations.

    Optional refactor when needed: Split into
    - ComparableField(ABC) with the comparison operators.
    - ComparableColumnField(StringField) for the __init__ and get_sqlmodel_field implementation.
    """

    def __init__(self, column: Mapped[T]) -> None:
        """Initialize the string field with a database column.

        Args:
            column: The database column this field represents.
        """
        self._column = column

    def get_sqlmodel_field(self) -> Mapped[T]:
        """Get the string database column or property.

        Returns:
            The string column for database queries.
        """
        return self._column

    def __eq__(self, other: T) -> ComparableFieldExpression[T]:  # type: ignore[override]
        """Create an equality expression."""
        return ComparableFieldExpression(field=self, operator="==", value=other)

    def __ne__(self, other: T) -> ComparableFieldExpression[T]:  # type: ignore[override]
        """Create a not-equal expression."""
        return ComparableFieldExpression(field=self, operator="!=", value=other)
