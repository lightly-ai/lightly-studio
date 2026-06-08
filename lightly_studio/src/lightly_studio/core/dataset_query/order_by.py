"""Classes for order by expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union, cast

from sqlalchemy import ColumnElement, and_
from sqlalchemy.engine import Row
from sqlalchemy.orm import aliased
from sqlmodel import col
from sqlmodel.sql.expression import Select, SelectOfScalar
from typing_extensions import Self, TypeAlias, TypeVar

from lightly_studio import db_json
from lightly_studio.core.dataset_query.field import Field
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable

SelectQuery: TypeAlias = Union[Select[Any], SelectOfScalar[Any]]
T = TypeVar("T", default=ImageTable)
ORDER_VALUE_LABEL = "order_value"


class OrderByExpression(ABC):
    """Base class for all order by expressions that can be applied to database queries."""

    def __init__(self, *, ascending: bool = True) -> None:
        """Initialize the order by expression.

        Args:
            ascending: Whether to order in ascending (True) or descending (False) order.
        """
        self.ascending = ascending

    @abstractmethod
    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the SQL expression used for sorting (no ASC/DESC)."""

    @abstractmethod
    def _apply_joins(self, query: SelectQuery) -> SelectQuery:
        """Add any JOINs needed so ``_order_value_expression()`` is valid on this query.

        Called by ``apply()`` and ``apply_with_options()`` before ORDER BY or
        ``add_columns``. Does not sort.
        Each subclass must implement this — return the query unchanged when the sort
        column is already reachable from the FROM clause (e.g. image-table fields).
        Use per-instance aliases when joining the same table more than once.
        """

    def to_column_element(self) -> ColumnElement[Any]:
        """Return the SQLAlchemy column element with direction applied.

        For use in ``query.order_by()`` or window ``over(order_by=...)``. Does not
        apply joins; call ``apply`` first when joins are required.
        """
        order_expr = self._order_value_expression()
        if self.ascending:
            return order_expr.asc()
        return order_expr.desc()

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply joins for this sort and append the ``ORDER BY``.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The modified query after joining and ordering.
        """
        joined = cast(SelectOfScalar[T], self._apply_joins(query))
        return joined.order_by(self.to_column_element())

    def apply_with_options(
        self,
        query: SelectQuery,
        order: bool = True,
        add_order_value: bool = True,
    ) -> SelectQuery:
        """Apply this sort and optionally append its value to the SELECT list.

        Behaves like ``apply`` but can also append the sort value to the SELECT list
        as ``ORDER_VALUE_LABEL``. Read values back with ``get_order_value``.

        Args:
            query: The SQLModel Select query to modify.
            order: When True, append ``ORDER BY`` using the directed sort expression.
                Pass False when ordering is handled separately (e.g. window functions).
            add_order_value: When True, append the sort value to the SELECT list as
                ``ORDER_VALUE_LABEL``. Pass False to apply joins (and ordering) only,
                e.g. when this expression contributes joins but its value is not needed.

        Returns:
            The modified query after joining, optionally appending the sort value, and
            optionally ordering.
        """
        query = self._apply_joins(query)
        if add_order_value:
            order_expr = self._order_value_expression()
            query = cast(SelectQuery, query.add_columns(order_expr.label(ORDER_VALUE_LABEL)))
        if order:
            query = query.order_by(self.to_column_element())
        return query

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

    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the image table column used for sorting."""
        return cast(ColumnElement[Any], self.field.get_sqlmodel_field())

    def _apply_joins(self, query: SelectQuery) -> SelectQuery:
        """Image-table fields are already in the FROM clause; no joins needed."""
        return query


class OrderByMetadataField(OrderByExpression):
    """Order by a field stored inside the SampleMetadataTable JSON data column.

    A LEFT OUTER JOIN to SampleMetadataTable is added automatically so that
    samples without metadata still appear in results (sorted last when ascending).

    Args:
        field_name: The key inside the JSON ``data`` column to sort by.
        cast_to_float: When True, the extracted value is cast to float before
            ordering.  Use this for numerical metadata fields so that numeric
            ordering is applied instead of lexicographic ordering.
    """

    def __init__(self, field_name: str, cast_to_float: bool) -> None:
        """Initialize with the metadata field name and float cast flag."""
        super().__init__()
        self.field_name = field_name
        # TODO(Leonardo, 05/2026): Rework to avoid requiring callers to pass
        # cast_to_float explicitly.
        self.cast_to_float = cast_to_float
        # Per-instance alias so sort joins do not collide with filter joins on metadata.
        self._metadata_alias = aliased(SampleMetadataTable)

    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the JSON-extract expression for the metadata field."""
        return db_json.json_extract(
            column=self._metadata_alias.data,
            field=self.field_name,
            cast_to_float=self.cast_to_float,
        )

    def _apply_joins(self, query: SelectQuery) -> SelectQuery:
        """Left-outer-join aliased ``SampleMetadataTable`` on ``sample_id``."""
        return query.outerjoin(
            self._metadata_alias,
            col(self._metadata_alias.sample_id) == col(ImageTable.sample_id),
        )


class OrderByEvaluationMetricField(OrderByExpression):
    """Order by an evaluation metric value from EvaluationSampleMetricTable.

    Two LEFT OUTER JOINs are added automatically: first to EvaluationRunTable
    (filtering by name) to resolve the run UUID, then to EvaluationSampleMetricTable
    (filtering by run ID, sample ID, and metric name) to get at most one row per sample.
    Samples without a metric value still appear in results (sorted last when ascending).

    Args:
        evaluation_run_name: The name of the evaluation run to sort by.
        metric_name: The metric name to sort by.
    """

    def __init__(self, evaluation_run_name: str, metric_name: str) -> None:
        """Initialize with the evaluation run name and metric name."""
        super().__init__()
        self.evaluation_run_name = evaluation_run_name
        self.metric_name = metric_name
        # Per-instance aliases so that multiple OrderByEvaluationMetricField
        # expressions in the same query each join distinct table aliases and
        # reference distinct value columns — avoiding ambiguous/duplicate SQL.
        self._run_alias = aliased(EvaluationRunTable)
        self._metric_alias = aliased(EvaluationSampleMetricTable)

    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the evaluation metric value column from the per-instance alias."""
        return cast(ColumnElement[Any], col(self._metric_alias.value))

    def _apply_joins(self, query: SelectQuery) -> SelectQuery:
        """Left-outer-join evaluation run and sample-metric tables."""
        query = query.outerjoin(
            self._run_alias,
            col(self._run_alias.name) == self.evaluation_run_name,
        )
        return query.outerjoin(
            self._metric_alias,
            and_(
                col(self._metric_alias.sample_id) == col(ImageTable.sample_id),
                col(self._metric_alias.evaluation_run_id) == col(self._run_alias.id),
                col(self._metric_alias.metric_name) == self.metric_name,
            ),
        )


def get_order_value(row: Row[Any]) -> Any | None:
    """Read the sort value from a row produced by ``apply_with_options``."""
    return getattr(row, ORDER_VALUE_LABEL, None)
