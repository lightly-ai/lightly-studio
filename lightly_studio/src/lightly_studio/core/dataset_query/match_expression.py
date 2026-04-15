"""Base classes for match expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import ColumnElement


class MatchExpression(ABC):
    """Base class for all match expressions that can be applied to database queries.

    This class provides the foundation for implementing complex query expressions
    that can be combined using AND/OR operations in the future.
    """

    @abstractmethod
    def get(self) -> ColumnElement[bool]:
        """Get the SQLAlchemy expression for this match expression.

        Returns:
            The combined SQLAlchemy expression.
        """

    @abstractmethod
    def to_wire(self) -> dict[str, Any]:
        """Serialise this expression to the canonical wire-format dict.

        The returned dict is JSON-serialisable and matches the schema consumed
        by the frontend and the ``WireExpression`` Pydantic model in
        ``core.dataset_query.wire``.
        """
