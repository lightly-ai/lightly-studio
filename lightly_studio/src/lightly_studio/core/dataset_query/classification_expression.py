"""Classes and functions for building complex queries against classification annotations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_expression import (
    ObjectDetectionComparableField,
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


class ClassificationField:
    """Providing access to predefined classification fields for queries."""

    # TODO(lukas, 04/2026): Rename ObjectDetectionComparableField to a different name, but only do
    # it once we also have InstanceSegmentationField class and requirements are more clear.
    label = ObjectDetectionComparableField(col(AnnotationLabelTable.annotation_label_name))


class ClassificationQuery:
    """Provides access to classification query operations."""

    @staticmethod
    def match(*criteria: MatchExpression) -> ClassificationMatchExpression:
        """Combine multiple classification criteria into a single subquery using logical AND.

        Args:
            criteria: The criteria to combine.

        Returns:
            A single match expression for satisfying all criteria.
        """
        return ClassificationMatchExpression(criterion=AND(*criteria))


@dataclass
class ClassificationMatchExpression(MatchExpression):
    """Expression for checking if a sample has a classification matching a criterion."""

    criterion: MatchExpression

    def get(self) -> ColumnElement[bool]:
        """Get the classification match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.CLASSIFICATION,
                self.criterion.get(),
            )
        )
