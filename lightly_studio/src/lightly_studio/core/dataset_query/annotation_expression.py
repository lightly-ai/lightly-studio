"""Annotation field classes for building dataset queries on sample annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Optional

from sqlalchemy import ColumnElement, and_
from sqlalchemy.orm import Mapped
from sqlmodel import col
from typing_extensions import TypeVar

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

    def __gt__(self, other: float | int) -> ObjectDetectionMatchExpression:
        """Create a greater-than expression."""
        return ObjectDetectionMatchExpression(
            criterion=self.field.__gt__(other),
            relationship=AnnotationBaseTable.object_detection_details,
        )

    def __lt__(self, other: float | int) -> ObjectDetectionMatchExpression:
        """Create a less-than expression."""
        return ObjectDetectionMatchExpression(
            self.field.__lt__(other),
            relationship=AnnotationBaseTable.object_detection_details,
        )

    def __ge__(self, other: float | int) -> ObjectDetectionMatchExpression:
        """Create a greater-than-or-equal expression."""
        return ObjectDetectionMatchExpression(
            self.field.__ge__(other),
            relationship=AnnotationBaseTable.object_detection_details,
        )

    def __le__(self, other: float | int) -> ObjectDetectionMatchExpression:
        """Create a less-than-or-equal expression."""
        return ObjectDetectionMatchExpression(
            self.field.__le__(other),
            relationship=AnnotationBaseTable.object_detection_details,
        )

    def __eq__(self, other: Any) -> ObjectDetectionMatchExpression:  # type: ignore[override]
        """Create an equality expression."""
        return ObjectDetectionMatchExpression(
            self.field.__eq__(other),
            relationship=AnnotationBaseTable.object_detection_details,
        )

    def __ne__(self, other: Any) -> ObjectDetectionMatchExpression:  # type: ignore[override]
        """Create a not-equal expression."""
        return ObjectDetectionMatchExpression(
            self.field.__ne__(other),
            relationship=AnnotationBaseTable.object_detection_details,
        )


# Ignore PLW1641 because `==` and `!=` create query conditions here, so these
# classes do not need normal hash behavior.
class ObjectDetectionComparableField:  # noqa: PLW1641
    """Comparable field for object detection properties."""

    def __init__(
        self,
        column: Mapped[Any],
    ) -> None:
        """Initialize the object detection comparable field.

        Args:
            column: The database column this field represents.
        """
        self.field = ComparableField(column)

    def __eq__(self, other: Any) -> ObjectDetectionMatchExpression[AnnotationLabelTable]:  # type: ignore[override]
        """Create an equality expression."""
        return ObjectDetectionMatchExpression(
            criterion=self.field.__eq__(other), relationship=AnnotationBaseTable.annotation_label
        )

    def __ne__(self, other: Any) -> ObjectDetectionMatchExpression[AnnotationLabelTable]:  # type: ignore[override]
        """Create a not-equal expression."""
        return ObjectDetectionMatchExpression(
            criterion=self.field.__ne__(other), relationship=AnnotationBaseTable.annotation_label
        )


class ObjectDetectionAccessor:
    """Provides access to object detection query operations."""

    # TODO(lukas, 4/2026): make confidence work too
    # confidence = NumericalField(col(AnnotationBaseTable.confidence))
    width = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.width))
    height = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.height))
    x = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.x))
    y = ObjectDetectionNumericalField(col(ObjectDetectionAnnotationTable.y))
    label = ObjectDetectionComparableField(
        col(AnnotationLabelTable.annotation_label_name),
    )


class AnnotationAccessor:
    """Provides access to query operations on sample annotations."""

    def object_detections(self) -> ObjectDetectionAccessor:
        """Return the accessor for querying object detection annotations."""
        return ObjectDetectionAccessor()


@dataclass
class ObjectDetectionMatchExpression(MatchExpression, Generic[T]):
    """Expression for checking if a sample has an object detection matching a criterion."""

    criterion: MatchExpression
    relationship: Mapped[T]

    def get(self) -> ColumnElement[bool]:
        """Get the object detection match expression."""
        condition = self.relationship.has(self.criterion.get())
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION,
                condition,
            )
        )
