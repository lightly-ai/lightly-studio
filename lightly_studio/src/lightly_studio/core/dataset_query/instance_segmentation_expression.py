"""Classes and functions for building complex queries against segmentation mask annotations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.boolean_expression import AND
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


class InstanceSegmentationField:
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
    label = ForeignComparableField(
        column=col(AnnotationLabelTable.annotation_label_name),
        relationship=AnnotationBaseTable.annotation_label,
    )


class InstanceSegmentationQuery:
    """Provides access to segmentation mask query operations."""

    @staticmethod
    def match(*criteria: MatchExpression) -> InstanceSegmentationMatchExpression:
        """Combine multiple segmentation mask criteria into a single subquery using logical AND.

        Args:
            criteria: The criteria to combine.

        Returns:
            A single match expression for satisfying all criteria.
        """
        return InstanceSegmentationMatchExpression(criterion=AND(*criteria))


@dataclass
class InstanceSegmentationMatchExpression(MatchExpression):
    """Expression for checking if a sample has an segmentation mask matching a criterion."""

    criterion: MatchExpression

    def get(self) -> ColumnElement[bool]:
        """Get the segmentation mask match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.SEGMENTATION_MASK,
                self.criterion.get(),
            )
        )
