"""Classes for order by expressions in dataset queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import ColumnElement
from sqlmodel import col
from sqlmodel.sql.expression import SelectOfScalar
from typing_extensions import Self, TypeVar

from lightly_studio import db_json
from lightly_studio.core.dataset_query.field import Field
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable

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

    @abstractmethod
    def to_column_element(self) -> ColumnElement[Any]:
        """Return the SQLAlchemy column element with direction applied.

        Returns:
            A column element ordered ascending or descending.
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

    def to_column_element(self) -> ColumnElement[Any]:
        """Return the JSON-extract column element with direction applied.

        Returns:
            A column element ordered ascending or descending.
        """
        extract_expr = db_json.json_extract(
            column=SampleMetadataTable.data,
            field=self.field_name,
            cast_to_float=self.cast_to_float,
        )
        if self.ascending:
            return extract_expr.asc()
        return extract_expr.desc()

    def apply(self, query: SelectOfScalar[T]) -> SelectOfScalar[T]:
        """Apply this ordering to a SQLModel Select query.

        Joins SampleMetadataTable (left outer join) and adds an ORDER BY clause
        on the extracted JSON field.

        Args:
            query: The SQLModel Select query to modify.

        Returns:
            The modified query after joining and ordering.
        """
        query = query.outerjoin(
            SampleMetadataTable,
            SampleMetadataTable.sample_id == col(ImageTable.sample_id),  # type: ignore[arg-type]
        )
        extract_expr = db_json.json_extract(
            column=SampleMetadataTable.data,
            field=self.field_name,
            cast_to_float=self.cast_to_float,
        )
        if self.ascending:
            return query.order_by(extract_expr.asc())
        return query.order_by(extract_expr.desc())
