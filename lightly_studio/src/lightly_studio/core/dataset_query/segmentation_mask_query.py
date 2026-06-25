"""Classes and functions for building complex queries against segmentation mask annotations."""

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
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


class SegmentationMaskField:
    """Providing access to predefined segmentation mask fields for queries."""

    width = ForeignNumericalField(
        column=col(SegmentationAnnotationTable.width),
        relationship=AnnotationBaseTable.segmentation_details,
    )
    height = ForeignNumericalField(
        column=col(SegmentationAnnotationTable.height),
        relationship=AnnotationBaseTable.segmentation_details,
    )
    x = ForeignNumericalField(
        column=col(SegmentationAnnotationTable.x),
        relationship=AnnotationBaseTable.segmentation_details,
    )
    y = ForeignNumericalField(
        column=col(SegmentationAnnotationTable.y),
        relationship=AnnotationBaseTable.segmentation_details,
    )
    class_name = ForeignComparableField(
        column=col(AnnotationLabelTable.annotation_label_name),
        relationship=AnnotationBaseTable.annotation_label,
    )
    source = AnnotationSourceField()
    confidence = NullableOrdinalField(col(AnnotationBaseTable.confidence))


class SegmentationMaskQuery(MatchExpression):
    """Query if a sample has a segmentation mask matching a criterion."""

    criterion: MatchExpression

    def __init__(self, *criteria: MatchExpression) -> None:
        """Combine multiple segmentation mask criteria into a single expression using AND.

        Example:
            ``SegmentationMaskQuery(SegmentationMaskField.width <= 100)``

        Args:
            criteria: The segmentation mask criteria to combine.
        """
        self.criterion = AND(*criteria)

    def get(self) -> ColumnElement[bool]:
        """Get the segmentation mask match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.SEGMENTATION_MASK,
                self.criterion.get(),
            )
        )
