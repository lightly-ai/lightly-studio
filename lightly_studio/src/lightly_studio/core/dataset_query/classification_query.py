"""Classes and functions for building complex queries against classification annotations."""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.annotation_expression import AnnotationSourceField
from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.field import NullableOrdinalField
from lightly_studio.core.dataset_query.foreign_field import ForeignComparableField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


class ClassificationField:
    """Providing access to predefined classification fields for queries."""

    class_name = ForeignComparableField(
        column=col(AnnotationLabelTable.annotation_label_name),
        relationship=AnnotationBaseTable.annotation_label,
    )
    source = AnnotationSourceField()
    confidence = NullableOrdinalField(col(AnnotationBaseTable.confidence))


class ClassificationQuery(MatchExpression):
    """Query if a sample has a classification matching a criterion."""

    criterion: MatchExpression

    def __init__(self, *criteria: MatchExpression) -> None:
        """Combine multiple classification criteria into a single expression using AND.

        Example:
            ``ClassificationQuery(ClassificationField.class_name == "cat")``

        Args:
            criteria: The classification criteria to combine.
        """
        self.criterion = AND(*criteria)

    def get(self) -> ColumnElement[bool]:
        """Get the classification match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.CLASSIFICATION,
                self.criterion.get(),
            )
        )
