"""Classes and functions for building complex queries against annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Mapped

from lightly_studio.core.dataset_query.match_expression import MatchExpression

T = TypeVar("T")


@dataclass
class RelationshipMatchExpression(MatchExpression, Generic[T]):
    """Match expression that evaluates a criterion against a relationship."""

    criterion: MatchExpression
    relationship: Mapped[T]

    def get(self) -> ColumnElement[bool]:
        """Get the relationship match expression."""
        return self.relationship.has(self.criterion.get())
