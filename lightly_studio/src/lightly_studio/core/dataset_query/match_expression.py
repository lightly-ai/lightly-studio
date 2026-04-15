"""Base classes for match expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod

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
