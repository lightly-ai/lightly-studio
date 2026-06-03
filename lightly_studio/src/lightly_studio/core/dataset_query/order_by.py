"""Classes for order by expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union, cast

from sqlalchemy import ColumnElement, and_
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

T = TypeVar("T", default=ImageTable)

SelectQuery: TypeAlias = Union[Select[Any], SelectOfScalar[Any]]


class OrderByExpression(ABC):
    """Base class for all order by expressions that can be applied to database queries."""

    def __init__(self, *, ascending: bool = True) -> None:
        """Initialize the order by expression.

        Args:
            ascending: Whether to order in ascending (True) or descending (False) order.
        """
        self.ascending = ascending

    @abstractmethod
    def _sort_value_expression(self) -> ColumnElement[Any] | None:
        """Return the undirected SQL expression used for sorting, if selectable.

        Used for ``ImageView.order_value`` when exposed via ``apply_select_join``.
        """

    def _apply_joins(self, query: SelectQuery) -> SelectQuery:
        """Apply joins required before sort expressions are valid in SQL."""
        return query

    def apply_select_join(
        self,
        query: SelectQuery,
        *,
        add_order_value: bool = False,
    ) -> tuple[SelectQuery, int | None]:
        """Apply joins required for this sort; optionally append sort value to SELECT.

        Args:
            query: The SQLModel Select query to modify.
            add_order_value: When True and this expression has a sort value, append it
                to the SELECT list (row index 1).

        Returns:
            The modified query and the sort-value column index, or ``None``.
        """
        query = self._apply_joins(query)
        order_value_index: int | None = None
        if add_order_value:
            sort_expr = self._sort_value_expression()
            if sort_expr is not None:
                query = cast(SelectQuery, query.add_columns(sort_expr))
                order_value_index = 1
        return query, order_value_index

    def to_column_element(self) -> ColumnElement[Any]:
        """Return the SQLAlchemy column element with direction applied.

        For use in ``query.order_by()`` or window ``over(order_by=...)``. Does not
        apply joins; call ``apply_select_join`` first when joins are required.
        """
        sort_expr = self._sort_value_expression()
        if sort_expr is None:
            msg = f"{type(self).__name__} has no sort value expression"
            raise NotImplementedError(msg)
        if self.ascending:
            return sort_expr.asc()
        return sort_expr.desc()

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply joins and ORDER BY for this sort expression."""
        updated, _ = self.apply_select_join(query)
        return cast(SelectOfScalar[T], updated.order_by(self.to_column_element()))

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

    def _sort_value_expression(self) -> ColumnElement[Any]:
        """Return the image table column used for sorting."""
        return cast(ColumnElement[Any], self.field.get_sqlmodel_field())


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

    def _sort_value_expression(self) -> ColumnElement[Any]:
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

    def _sort_value_expression(self) -> ColumnElement[Any]:
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
