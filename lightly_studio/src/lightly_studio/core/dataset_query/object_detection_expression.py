"""Classes and functions for building complex queries against object detection annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import ColumnElement, and_
from sqlmodel import col
from typing_extensions import TypeVar

from lightly_studio.core.dataset_query.annotation_expression import (
    AnnotationComparableField,
    AnnotationNumericalField,
)
from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable

T = TypeVar("T", default=Optional["ObjectDetectionAnnotationTable"])


class ObjectDetectionField:
    """Providing access to predefined object detection fields for queries."""

    width = AnnotationNumericalField(
        col(ObjectDetectionAnnotationTable.width),
        AnnotationBaseTable.object_detection_details,
    )
    height = AnnotationNumericalField(
        col(ObjectDetectionAnnotationTable.height),
        AnnotationBaseTable.object_detection_details,
    )
    x = AnnotationNumericalField(
        col(ObjectDetectionAnnotationTable.x),
        AnnotationBaseTable.object_detection_details,
    )
    y = AnnotationNumericalField(
        col(ObjectDetectionAnnotationTable.y),
        AnnotationBaseTable.object_detection_details,
    )
    label = AnnotationComparableField(
        col(AnnotationLabelTable.annotation_label_name),
        AnnotationBaseTable.annotation_label,
    )
    # TODO(lukas, 4/2026): add confidence


class ObjectDetectionQuery:
    """Provides access to object detection query operations."""

    @staticmethod
    def match(*criteria: MatchExpression) -> ObjectDetectionMatchExpression:
        """Combine multiple object detection criteria into a single subquery using logical AND.

        Args:
            criteria: The criteria to combine.

        Returns:
            A single match expression for satisfying all criteria.
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
