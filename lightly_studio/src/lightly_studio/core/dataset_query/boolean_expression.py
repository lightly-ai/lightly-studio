"""Classes for boolean expressions in dataset queries."""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, false, not_, or_, true

from lightly_studio.core.dataset_query.match_expression import MatchExpression


class AND(MatchExpression):
    """Logical AND operation between other MatchExpression objects."""

    def __init__(self, *terms: MatchExpression) -> None:
        """Initialize AND Expression with multiple MatchExpression terms.

        Args:
            terms: The MatchExpression instances to combine with AND. They can also be nested.
        """
        self.terms = terms

    def get(self) -> ColumnElement[bool]:
        """Combine expressions of all terms using AND.

        Returns:
            The combined SQLAlchemy expression.
        """
        return and_(true(), *(term.get() for term in self.terms))


class OR(MatchExpression):
    """Logical OR operation between other MatchExpression objects."""

    def __init__(self, *terms: MatchExpression) -> None:
        """Initialize OR Expression with multiple MatchExpression terms.

        Args:
            terms: The MatchExpression instances to combine with OR. They can also be nested.
        """
        self.terms = terms

    def get(self) -> ColumnElement[bool]:
        """Combine expressions of all terms using OR.

        Returns:
            The combined SQLAlchemy expression.
        """
        return or_(false(), *(term.get() for term in self.terms))


class NOT(MatchExpression):
    """Logical NOT operation for a MatchExpression object."""

    def __init__(self, term: MatchExpression) -> None:
        """Initialize NOT Expression with a MatchExpression term.

        Args:
            term: The MatchExpression to be negated. It can also be nested.
        """
        self.term = term

    def get(self) -> ColumnElement[bool]:
        """Negate the expression of the term using NOT.

        Returns:
            The combined SQLAlchemy expression.
        """
        return not_(self.term.get())
