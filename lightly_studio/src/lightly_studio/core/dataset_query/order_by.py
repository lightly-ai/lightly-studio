"""Classes for order by expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast

import sqlalchemy
from sqlalchemy import ColumnElement, and_
from sqlalchemy import Select as SQLAlchemySelect
from sqlalchemy.engine import Row
from sqlalchemy.orm import aliased
from sqlmodel import col
from sqlmodel.sql.expression import SelectOfScalar
from typing_extensions import Self, TypeVar

from lightly_studio.core.dataset_query.field import Field
from lightly_studio.database import db_json
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import NUMERIC_TYPE_NAMES, SampleMetadataTable
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
        """Return the value surfaced by ``apply_with_order_value`` (no ASC/DESC)."""

    def _sort_key_expressions(self) -> list[ColumnElement[Any]]:
        """Return the SQL expressions to sort by, most significant first (no ASC/DESC).

        Defaults to the order value alone. Override when correct ordering needs more
        than one key.
        """
        return [self._order_value_expression()]

    @abstractmethod
    def apply_joins(self, query: SelectT) -> SelectT:
        """Add any JOINs needed so ``_order_value_expression()`` is valid on this query.

        Called by ``apply()`` and ``apply_with_order_value()`` before ORDER BY or
        ``add_columns``. Does not sort.
        Each subclass must implement this — return the query unchanged when the sort
        column is already reachable from the FROM clause (e.g. image-table fields).
        Use per-instance aliases when joining the same table more than once.
        """

    def to_column_elements(self) -> list[ColumnElement[Any]]:
        """Return the SQLAlchemy column elements with direction applied.

        For use in ``query.order_by()`` or window ``over(order_by=...)``. Usually a
        single element; a sort may return several when one key cannot express the
        required ordering. Does not apply joins; call ``apply`` first when joins are
        required.
        """
        if self.ascending:
            return [expr.asc() for expr in self._sort_key_expressions()]
        return [expr.desc() for expr in self._sort_key_expressions()]

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply joins for this sort and append the ``ORDER BY``.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The modified query after joining and ordering.
        """
        joined = self.apply_joins(query)
        return joined.order_by(*self.to_column_elements())

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
        order_value = self._order_value_expression().label(ORDER_VALUE_LABEL)
        return joined.add_columns(order_value).order_by(*self.to_column_elements())

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

    Numerical fields order numerically and everything else lexicographically,
    decided in SQL from the type recorded in ``metadata_schema``. Only top-level
    keys are recorded there, so a dotted path sorts lexicographically.

    Args:
        field_name: The key inside the JSON ``data`` column to sort by.
    """

    def __init__(self, field_name: str) -> None:
        """Initialize with the metadata field name."""
        super().__init__()
        self.field_name = field_name
        # Per-instance alias so sort joins do not collide with filter joins on metadata.
        self._metadata_alias = aliased(SampleMetadataTable)

    def _order_value_expression(self) -> ColumnElement[Any]:
        """Return the numerical value of the field, or NULL if it is not numerical.

        The CAST wraps the CASE so its operand is NULL for rows that would fail it,
        and casts to Double because DuckDB's FLOAT is single precision.
        """
        return sqlalchemy.cast(
            sqlalchemy.case(
                (self._is_numerical_field(), self._extracted_value()),
                else_=None,
            ),
            sqlalchemy.Double,
        )

    def _sort_key_expressions(self) -> list[ColumnElement[Any]]:
        """Return the numerical key, NULL for non-numerical fields, then the raw value."""
        return [self._order_value_expression(), self._extracted_value()]

    def to_column_elements(self) -> list[ColumnElement[Any]]:
        """Pin NULLs last; the two dialects disagree on where they go by default."""
        return [sqlalchemy.nullslast(element) for element in super().to_column_elements()]

    def _is_numerical_field(self) -> ColumnElement[bool]:
        """Return whether ``metadata_schema`` records this field as a number.

        Uses the same path syntax as the value, so the two cannot disagree.
        """
        return db_json.json_extract(
            column=self._metadata_alias.metadata_schema,
            field=self.field_name,
        ).in_([db_json.json_literal(type_name) for type_name in NUMERIC_TYPE_NAMES])

    def _extracted_value(self) -> ColumnElement[Any]:
        """Return the raw JSON value of the field."""
        return db_json.json_extract(column=self._metadata_alias.data, field=self.field_name)

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


def get_order_value(row: Row[Any]) -> Any | None:
    """Read the sort value from a row produced by ``apply_with_order_value``."""
    return getattr(row, ORDER_VALUE_LABEL, None)
