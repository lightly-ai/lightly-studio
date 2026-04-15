"""Classes and functions for building complex queries against instance segmentation annotations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

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
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


class InstanceSegmentationField:
    """Providing access to predefined instance segmentation fields for queries."""

    width = AnnotationNumericalField(
        col(SegmentationAnnotationTable.width),
        AnnotationBaseTable.segmentation_details,
    )
    height = AnnotationNumericalField(
        col(SegmentationAnnotationTable.height),
        AnnotationBaseTable.segmentation_details,
    )
    x = AnnotationNumericalField(
        col(SegmentationAnnotationTable.x),
        AnnotationBaseTable.segmentation_details,
    )
    y = AnnotationNumericalField(
        col(SegmentationAnnotationTable.y),
        AnnotationBaseTable.segmentation_details,
    )
    segmentation_mask = AnnotationComparableField(
        col(SegmentationAnnotationTable.segmentation_mask),
        AnnotationBaseTable.segmentation_details,
    )
    label = AnnotationComparableField(
        col(AnnotationLabelTable.annotation_label_name),
        AnnotationBaseTable.annotation_label,
    )


class InstanceSegmentationQuery:
    """Provides access to instance segmentation query operations."""

    @staticmethod
    def match(*criteria: MatchExpression) -> InstanceSegmentationMatchExpression:
        """Combine multiple instance segmentation criteria into a single subquery using logical AND.

        Args:
            criteria: The criteria to combine.

        Returns:
            A single match expression for satisfying all criteria.
        """
        return InstanceSegmentationMatchExpression(criterion=AND(*criteria))


@dataclass
class InstanceSegmentationMatchExpression(MatchExpression):
    """Expression for checking if a sample has an instance segmentation matching a criterion."""

    criterion: MatchExpression

    def get(self) -> ColumnElement[bool]:
        """Get the instance segmentation match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.INSTANCE_SEGMENTATION,
                self.criterion.get(),
            )
        )
