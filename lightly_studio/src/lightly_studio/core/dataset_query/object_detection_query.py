"""Classes and functions for building complex queries against object detection annotations."""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.annotation_expression import AnnotationSourceField
from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.field import NullableOrdinalField
from lightly_studio.core.dataset_query.foreign_field import (
    ForeignComparableField,
    ForeignNumericalField,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


class ObjectDetectionField:
    """Providing access to predefined object detection fields for queries."""

    width = ForeignNumericalField(
        column=col(ObjectDetectionAnnotationTable.width),
        relationship=AnnotationBaseTable.object_detection_details,
    )
    height = ForeignNumericalField(
        column=col(ObjectDetectionAnnotationTable.height),
        relationship=AnnotationBaseTable.object_detection_details,
    )
    x = ForeignNumericalField(
        column=col(ObjectDetectionAnnotationTable.x),
        relationship=AnnotationBaseTable.object_detection_details,
    )
    y = ForeignNumericalField(
        column=col(ObjectDetectionAnnotationTable.y),
        relationship=AnnotationBaseTable.object_detection_details,
    )
    class_name = ForeignComparableField(
        column=col(AnnotationLabelTable.annotation_label_name),
        relationship=AnnotationBaseTable.annotation_label,
    )
    source = AnnotationSourceField()
    confidence = NullableOrdinalField(col(AnnotationBaseTable.confidence))


class ObjectDetectionQuery(MatchExpression):
    """Query if a sample has an object detection matching a criterion."""

    criterion: MatchExpression

    def __init__(self, *criteria: MatchExpression) -> None:
        """Combine multiple object detection criteria into a single expression using AND.

        Example:
            ``ObjectDetectionQuery(ObjectDetectionField.width <= 100)``

        Args:
            criteria: The object detection criteria to combine.
        """
        self.criterion = AND(*criteria)

    def get(self) -> ColumnElement[bool]:
        """Get the object detection match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.OBJECT_DETECTION,
                self.criterion.get(),
            )
        )
