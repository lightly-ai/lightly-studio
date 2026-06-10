"""Classes and functions for building complex queries against annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Mapped
from sqlmodel import col

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample import SampleTable

T = TypeVar("T")


# Ignore PLW1641 because `==` and `!=` create query conditions here, so these
# classes do not need normal hash behavior.
@dataclass
class RelationshipMatchExpression(MatchExpression, Generic[T]):
    """Evaluates a match expression against a related table using the SQLAlchemy `.has()` operator.

    This expression is used to filter records based on properties in a related table,
    such as querying annotations by their associated label name.

    # Example
    To filter annotations by label name without this helper, you would use:
    ```python
    AnnotationBaseTable.annotation_label.has(
        col(AnnotationLabelTable.annotation_label_name) == "label1"
    )
    ```

    `RelationshipMatchExpression` simplifies such a field-level comparison, applying it through the
    specified relationship and returning a `MatchExpression`:
    ```python
    field = ComparableField(col(AnnotationLabelTable.annotation_label_name))

    def __eq__(self, other: Any) -> MatchExpression:
        return RelationshipMatchExpression(
            criterion=self.field.__eq__(other),
            relationship=AnnotationBaseTable.annotation_label
        )
    ```

    See e.g. `ObjectDetectionComparableField` which utilizes `RelationshipMatchExpression`.
    """

    criterion: MatchExpression
    relationship: Mapped[T]

    def get(self) -> ColumnElement[bool]:
        """Get the relationship match expression."""
        return self.relationship.has(self.criterion.get())


class AnnotationSourceField:
    """Queryable annotation source field."""

    __hash__ = object.__hash__

    def __eq__(self, other: str) -> MatchExpression:  # type: ignore[override]
        """Return a match expression for a source name equality check."""
        return AnnotationSourceMatchExpression(source_name=other)

    def __ne__(self, other: str) -> MatchExpression:  # type: ignore[override]
        """Return a match expression for a source name inequality check."""
        return AnnotationSourceMatchExpression(source_name=other, negate=True)


@dataclass
class AnnotationSourceMatchExpression(MatchExpression):
    """Evaluates an annotation source comparison against the owning collection."""

    source_name: str
    negate: bool = False

    def get(self) -> ColumnElement[bool]:
        """Get the annotation source match expression."""
        expr = AnnotationBaseTable.sample.has(
            SampleTable.collection.has(col(CollectionTable.name) == self.source_name)
        )
        return ~expr if self.negate else expr
