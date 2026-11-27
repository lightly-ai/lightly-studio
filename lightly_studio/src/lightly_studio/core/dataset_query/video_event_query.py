"""Queries for temporal classification annotations on videos."""

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.classification_query import ClassificationField
from lightly_studio.core.dataset_query.foreign_field import ForeignNumericalField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.temporal_span import TemporalSpanTable


class VideoEventField(ClassificationField):
    """Classification fields plus event start and end times.

    Attributes:
        start_time_s: Event start in seconds relative to the video start.
        end_time_s: Event end in seconds relative to the video start.
    """

    start_time_s = ForeignNumericalField(
        column=col(TemporalSpanTable.start_time_s),
        relationship=AnnotationBaseTable.temporal_span_details,
    )
    end_time_s = ForeignNumericalField(
        column=col(TemporalSpanTable.end_time_s),
        relationship=AnnotationBaseTable.temporal_span_details,
    )


class VideoEventQuery(MatchExpression):
    """Match a temporal classification annotation with all criteria on the same event."""

    def __init__(self, *criteria: MatchExpression) -> None:
        """Combine event criteria with AND.

        Args:
            criteria: Event fields and boolean expressions to match.
        """
        self.criterion = AND(*criteria)

    def get(self) -> ColumnElement[bool]:
        """Get the event match expression."""
        return SampleTable.annotations.any(
            and_(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.CLASSIFICATION,
                AnnotationBaseTable.temporal_span_details.has(),
                self.criterion.get(),
            )
        )
