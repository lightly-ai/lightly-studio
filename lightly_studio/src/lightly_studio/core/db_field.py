"""Database field descriptor."""

from __future__ import annotations

from typing import Any, Generic, Protocol, TypeVar

from sqlalchemy.orm import Mapped
from sqlmodel import Session

T = TypeVar("T")


class _DBFieldOwner(Protocol):
    inner: Any

    def get_object_session(self) -> Session: ...


class DBField(Generic[T]):
    """Descriptor for a database-backed field.

    Provides interface to a SQLAlchemy model field. Setting the field
    immediately commits to the database. The owner class must implement
    the inner attribute and the get_object_session() method.
    """

    __slots__ = ("_sqla_descriptor",)
    """Store the SQLAlchemy descriptor for accessing the field."""

    def __init__(self, sqla_descriptor: Mapped[T]) -> None:
        """Initialize the DBField with a SQLAlchemy descriptor."""
        self._sqla_descriptor = sqla_descriptor

    def __get__(self, obj: _DBFieldOwner | None, owner: type | None = None) -> T:
        """Get the value of the field from the database."""
        assert obj is not None, "DBField must be accessed via an instance, not the class"
        # Delegate to SQLAlchemy's descriptor.
        value: T = self._sqla_descriptor.__get__(obj.inner, type(obj.inner))
        return value

    def __set__(self, obj: _DBFieldOwner, value: T) -> None:
        """Set the value of the field in the database. Commits the session."""
        # Delegate to SQLAlchemy's descriptor.
        self._sqla_descriptor.__set__(obj.inner, value)
        obj.get_object_session().commit()
