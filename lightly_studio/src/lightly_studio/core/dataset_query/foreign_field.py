"""Classes and functions for building complex queries against foreign fields."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Mapped

from lightly_studio.core.dataset_query.annotation_expression import RelationshipMatchExpression
from lightly_studio.core.dataset_query.field import ComparableField, NumericalField
from lightly_studio.core.dataset_query.match_expression import MatchExpression

T = TypeVar("T")


# Ignore PLW1641 because `==` and `!=` create query conditions here, so these
# classes do not need normal hash behavior.
class ForeignComparableField(Generic[T]):  # noqa: PLW1641
    """Comparable field for properties on a related table."""

    def __init__(self, column: Mapped[Any], relationship: Mapped[T]) -> None:
        """Initialize the comparable foreign field.

        Args:
            column: The database column this field represents.
            relationship: The database relationship this field belongs to.
        """
        self.field = ComparableField(column)
        self.relationship = relationship

    def __eq__(self, other: Any) -> MatchExpression:  # type: ignore[override]
        """Create an equality expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__eq__(other), relationship=self.relationship
        )

    def __ne__(self, other: Any) -> MatchExpression:  # type: ignore[override]
        """Create a not-equal expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__ne__(other), relationship=self.relationship
        )


# Ignore PLW1641 because `==` and `!=` create query conditions here, so these
# classes do not need normal hash behavior.
class ForeignNumericalField(Generic[T]):  # noqa: PLW1641
    """Numerical field for properties on a related table."""

    def __init__(self, column: Mapped[int | float], relationship: Mapped[T]) -> None:
        """Initialize the numerical foreign field.

        Args:
            column: The database column this field represents.
            relationship: The database relationship this field belongs to.
        """
        self.field = NumericalField(column)
        self.relationship = relationship

    def __gt__(self, other: float | int) -> MatchExpression:
        """Create a greater-than expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__gt__(other), relationship=self.relationship
        )

    def __lt__(self, other: float | int) -> MatchExpression:
        """Create a less-than expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__lt__(other), relationship=self.relationship
        )

    def __ge__(self, other: float | int) -> MatchExpression:
        """Create a greater-than-or-equal expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__ge__(other), relationship=self.relationship
        )

    def __le__(self, other: float | int) -> MatchExpression:
        """Create a less-than-or-equal expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__le__(other), relationship=self.relationship
        )

    def __eq__(self, other: Any) -> MatchExpression:  # type: ignore[override]
        """Create an equality expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__eq__(other), relationship=self.relationship
        )

    def __ne__(self, other: Any) -> MatchExpression:  # type: ignore[override]
        """Create a not-equal expression."""
        return RelationshipMatchExpression(
            criterion=self.field.__ne__(other), relationship=self.relationship
        )
