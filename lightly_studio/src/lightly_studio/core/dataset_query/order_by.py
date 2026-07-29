"""Classes for order by expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast
from uuid import UUID

from sqlalchemy import ColumnElement, and_, case, func, nullslast, or_
from sqlalchemy import Select as SQLAlchemySelect
from sqlalchemy.engine import Row
from sqlalchemy.orm import Mapped, aliased
from sqlmodel import col
from sqlmodel.sql.expression import SelectOfScalar
from typing_extensions import Self, TypeVar

from lightly_studio.core.dataset_query.field import Field
from lightly_studio.database import db_json
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricTable,
    EvaluationAnnotationSide,
)
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable

T = TypeVar("T", default=ImageTable)
# Preserves the query type so apply_joins works on both SelectOfScalar (apply)
# and Select (window query).
SelectT = TypeVar("SelectT", bound=SQLAlchemySelect[Any])
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
    def apply_joins(self, query: SelectT) -> SelectT:
        """Add any JOINs needed so ``_order_value_expression()`` is valid on this query.

        Called by ``apply()`` and ``apply_with_order_value()`` before ORDER BY or
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

    def order_value_column(self) -> ColumnElement[Any]:
        """Return the sort value labeled for the SELECT list.

        For callers that build their own ``ORDER BY`` and only need the value appended
        to the row. Read values back with ``get_order_value``.
        """
        return self._order_value_expression().label(ORDER_VALUE_LABEL)

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply joins for this sort and append the ``ORDER BY``.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The modified query after joining and ordering.
        """
        joined = self.apply_joins(query)
        return joined.order_by(self.to_column_element())

    def apply_with_order_value(self, query: SelectOfScalar[T]) -> SQLAlchemySelect[tuple[T, Any]]:
        """Apply this sort and append its value to the SELECT list.

        Behaves like ``apply`` but also appends the sort value to the SELECT list as
        ``ORDER_VALUE_LABEL``. Read values back with ``get_order_value``. Returns a
        multi-column ``Select`` (read rows with ``session.execute``) because the sort
        value is added to the row.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The query after joining, appending the labeled sort value, and ordering.
        """
        joined = self.apply_joins(query)
        return joined.add_columns(self.order_value_column()).order_by(self.to_column_element())

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

    def apply_joins(self, query: SelectT) -> SelectT:
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

    def apply_joins(self, query: SelectT) -> SelectT:
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
        self._collection_alias = aliased(CollectionTable)

    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the evaluation metric value column from the per-instance alias."""
        return cast(ColumnElement[Any], col(self._metric_alias.value))

    def apply_joins(self, query: SelectT) -> SelectT:
        """Left-outer-join evaluation run and sample-metric tables."""
        query = query.outerjoin(
            self._collection_alias,
            col(self._collection_alias.collection_id) == col(SampleTable.collection_id),
        ).outerjoin(
            self._run_alias,
            and_(
                col(self._run_alias.name) == self.evaluation_run_name,
                col(self._run_alias.dataset_id) == col(self._collection_alias.dataset_id),
            ),
        )
        return query.outerjoin(
            self._metric_alias,
            and_(
                col(self._metric_alias.sample_id) == col(ImageTable.sample_id),
                col(self._metric_alias.evaluation_run_id) == col(self._run_alias.id),
                col(self._metric_alias.metric_name) == self.metric_name,
            ),
        )


class OrderByAnnotationEvaluationMetricField(OrderByExpression):
    """Order annotations by a per-annotation metric from EvaluationAnnotationMetricTable.

    A single LEFT OUTER JOIN is added, so annotations the run never covered still appear
    in results. Three states must stay distinguishable:

    - Matched pair: a metric value exists, order by it.
    - Unmatched annotation (false positive / false negative): a row exists but carries no
      metric name or value. A completely missed box genuinely has zero overlap, so it
      orders as ``0.0``.
    - Annotation absent from the run, because evaluation covered a subset of samples:
      no row at all, genuinely unknown, orders as ``NULL``.

    Distinguishing the last two is why the ordering value is keyed on whether the joined
    row exists rather than coalescing the value itself. Nulls are placed last in both
    directions so un-evaluated annotations never crowd out the top of the review queue.

    Args:
        evaluation_run_id: ID of the evaluation run holding the metric.
        metric_name: Name of the metric to order by, as stored.
        side: Which side of the run's pairing the browsed annotation source is. Selects
            the column the join matches the annotation ID against.
        annotation_id_column: Column holding the annotation's sample ID. Passed in
            because the grid query is rooted on the annotation table while adjacency
            orders over a filtered subquery.
    """

    def __init__(
        self,
        *,
        evaluation_run_id: UUID,
        metric_name: str,
        side: EvaluationAnnotationSide,
        annotation_id_column: ColumnElement[Any] | Mapped[Any],
    ) -> None:
        """Initialize with the run, metric, pairing side and annotation ID column."""
        super().__init__()
        self.evaluation_run_id = evaluation_run_id
        self.metric_name = metric_name
        self.side = side
        self.annotation_id_column = annotation_id_column
        # Per-instance alias so this join cannot collide with a filter join on the same table.
        self._metric_alias = aliased(EvaluationAnnotationMetricTable)

    def to_column_element(self) -> ColumnElement[Any]:
        """Return the sort value with direction applied and nulls placed last."""
        return nullslast(super().to_column_element())

    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the metric value, zero when the row is unmatched, null when absent."""
        return case(
            (
                col(self._metric_alias.id).is_not(None),
                func.coalesce(col(self._metric_alias.value), 0.0),
            ),
            else_=None,
        )

    def apply_joins(self, query: SelectT) -> SelectT:
        """Left-outer-join the aliased annotation metric table on the pairing side.

        The predicate matches the requested metric name or a null one, so a run writing
        several metrics per annotation cannot multiply grid rows and corrupt the count.
        """
        if self.side == EvaluationAnnotationSide.GROUND_TRUTH:
            side_column = col(self._metric_alias.gt_annotation_id)
        else:
            side_column = col(self._metric_alias.pred_annotation_id)

        return query.outerjoin(
            self._metric_alias,
            and_(
                side_column == self.annotation_id_column,
                col(self._metric_alias.evaluation_run_id) == self.evaluation_run_id,
                or_(
                    col(self._metric_alias.metric_name) == self.metric_name,
                    col(self._metric_alias.metric_name).is_(None),
                ),
            ),
        )


def get_order_value(row: Row[Any]) -> Any | None:
    """Read the sort value from a row produced by ``apply_with_order_value``."""
    return getattr(row, ORDER_VALUE_LABEL, None)
