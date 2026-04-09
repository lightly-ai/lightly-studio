"""Annotation queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Optional

from sqlalchemy import ColumnElement, and_
from sqlalchemy.orm import Mapped
from sqlmodel import col
from typing_extensions import TypeVar

from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.field import ComparableField, NumericalField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable

T = TypeVar("T", default=Optional["ObjectDetectionAnnotationTable"])


@dataclass
class RelationshipMatchExpression(MatchExpression, Generic[T]):
    """Match expression that evaluates a criterion against a relationship."""

    criterion: MatchExpression
    relationship: Mapped[T]

    def get(self) -> ColumnElement[bool]:
        """Get the relationship match expression."""
        return self.relationship.has(self.criterion.get())


# Ignore PLW1641 because `==` and `!=` create query conditions here, so these
# classes do not need normal hash behavior.
class ObjectDetectionNumericalField:  # noqa: PLW1641
    """Numerical field for object detection properties."""

    def __init__(self, column: Mapped[int | float]) -> None:
        """Initialize the object detection numerical field.

        Args:
            column: The database column this field represents.
        """
        self.field = NumericalField(column)
        self.relationship = AnnotationBaseTable.object_detection_details

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


# Ignore PLW1641 because `==` and `!=` create query conditions here, so these
# classes do not need normal hash behavior.
class ObjectDetectionComparableField:  # noqa: PLW1641
    """Comparable field for object detection properties."""

    def __init__(self, column: Mapped[Any]) -> None:
        """Initialize the object detection comparable field.

        Args:
            column: The database column this field represents.
        """
        self.field = ComparableField(column)
        self.relationship = AnnotationBaseTable.annotation_label

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


class ObjectDetectionField:
    """Providing access to predefined object detection fields for queries."""

    width = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.width))
    height = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.height))
    x = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.x))
    y = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.y))
    label = ObjectDetectionComparableField(col(AnnotationLabelTable.annotation_label_name))


class ObjectDetectionQuery:
    """Provides access to object detection query operations."""

    @staticmethod
    def match(*criteria: MatchExpression) -> ObjectDetectionMatchExpression:
        """Combine multiple object detection criteria into a single subquery.

        Args:
            criteria: The criteria to combine.

        Returns:
            A single match expression for the combined criteria.
        """
        return ObjectDetectionMatchExpression(criterion=AND(*criteria))


@dataclass
class ObjectDetectionMatchExpression(MatchExpression):
    """Expression for checking if a sample has an object detection matching a criterion."""

    criterion: MatchExpression

    def get(self) -> ColumnElement[bool]:
        """Get the object detection match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION,
                self.criterion.get(),
            )
        )


class AnnotationAccessor:
    """Provides access to query operations on sample annotations."""

    @property
    def object_detections(self) -> ObjectDetectionQuery:
        """Return the accessor for querying object detection annotations."""
        return ObjectDetectionQuery()
