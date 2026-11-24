"""Classes and functions for building complex queries against polygon annotations."""

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
from lightly_studio.models.annotation.polygon import PolygonAnnotationTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


class PolygonField:
    """Providing access to predefined polygon fields for queries.

    The bounding box is the smallest integer pixel box that contains all vertices of all
    polygon parts. Fractional vertices round outward.
    """

    width = ForeignNumericalField(
        column=col(PolygonAnnotationTable.width),
        relationship=AnnotationBaseTable.polygon_details,
    )
    """Width of the bounding box in pixels."""
    height = ForeignNumericalField(
        column=col(PolygonAnnotationTable.height),
        relationship=AnnotationBaseTable.polygon_details,
    )
    """Height of the bounding box in pixels."""
    x = ForeignNumericalField(
        column=col(PolygonAnnotationTable.x),
        relationship=AnnotationBaseTable.polygon_details,
    )
    """Left edge of the bounding box in pixels."""
    y = ForeignNumericalField(
        column=col(PolygonAnnotationTable.y),
        relationship=AnnotationBaseTable.polygon_details,
    )
    """Top edge of the bounding box in pixels."""
    class_name = ForeignComparableField(
        column=col(AnnotationLabelTable.annotation_label_name),
        relationship=AnnotationBaseTable.annotation_label,
    )
    source = AnnotationSourceField()
    confidence = NullableOrdinalField(col(AnnotationBaseTable.confidence))


class PolygonQuery(MatchExpression):
    """Query if a sample has a polygon matching a criterion."""

    criterion: MatchExpression

    def __init__(self, *criteria: MatchExpression) -> None:
        """Combine multiple polygon criteria into a single expression using AND.

        Example:
            ``PolygonQuery(PolygonField.width <= 100)``

        Args:
            criteria: The polygon criteria to combine.
        """
        self.criterion = AND(*criteria)

    def get(self) -> ColumnElement[bool]:
        """Get the polygon match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.POLYGON,
                self.criterion.get(),
            )
        )
