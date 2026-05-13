"""Classes for order by expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlmodel import col
from sqlmodel.sql.expression import SelectOfScalar
from typing_extensions import Self, TypeVar

from lightly_studio.core.dataset_query.field import Field
from lightly_studio.models.image import ImageTable

T = TypeVar("T", default=ImageTable)


class OrderByExpression(ABC):
    """Base class for all order by expressions that can be applied to database queries."""

    def __init__(self, *, ascending: bool = True) -> None:
        """Initialize the order by expression.

        Args:
            ascending: Whether to order in ascending (True) or descending (False) order.
        """
        self.ascending = ascending

    @abstractmethod
    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply this ordering to a SQLModel Select query.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The modified query after ordering
        """

    def asc(self) -> Self:
        """Set the ordering to ascending.

        Returns:
            Self for method chaining.
        """
        self.ascending = True
        return self

    def desc(self) -> Self:
        """Set the ordering to descending.

        Returns:
            Self for method chaining.
        """
        self.ascending = False
        return self


class OrderByField(OrderByExpression):
    """Order by a specific field, either ascending or descending.

    Args:
        field: The field to order by.
        ascending: Whether to order in ascending (True) or descending (False) order.
    """

    def __init__(self, field: Field) -> None:
        """Initialize with field and order direction."""
        super().__init__()
        self.field = field

    def to_column_element(self) -> ColumnElement[Any]:
        """Return the SQLAlchemy column element with direction applied.

        Returns:
            A column element ordered ascending or descending.
        """
        if self.ascending:
            return self.field.get_sqlmodel_field().asc()
        return self.field.get_sqlmodel_field().desc()

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply this ordering to a SQLModel Select query.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The modified query after ordering
        """
        if self.ascending:
            return query.order_by(self.field.get_sqlmodel_field().asc())
        return query.order_by(self.field.get_sqlmodel_field().desc())


class OrderByMetric(OrderByExpression):
    """Order images by a per-sample evaluation metric via a LEFT JOIN on EvaluationSampleMetric.

    Images without a metric value (not covered by the eval run) sort last.
    """

    def __init__(self, evaluation_run_id: UUID, metric_name: str) -> None:
        super().__init__()
        self.evaluation_run_id = evaluation_run_id
        self.metric_name = metric_name

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable

        query = query.outerjoin(
            EvaluationSampleMetricTable,
            (col(EvaluationSampleMetricTable.sample_id) == col(ImageTable.sample_id))
            & (col(EvaluationSampleMetricTable.evaluation_run_id) == self.evaluation_run_id)
            & (col(EvaluationSampleMetricTable.metric_name) == self.metric_name),
        )
        value = col(EvaluationSampleMetricTable.value)
        # NULLs (images with no metric value) always sort last regardless of direction
        if self.ascending:
            return query.order_by(
                value.is_(None).asc(), value.asc()
            )
        return query.order_by(
            value.is_(None).asc(), value.desc()
        )
