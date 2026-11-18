"""Field expressions for building specific query conditions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from sqlalchemy import ColumnElement, Float, cast
from sqlalchemy.orm import Mapped

from lightly_studio.core.dataset_query.match_expression import MatchExpression

if TYPE_CHECKING:
    from lightly_studio.core.dataset_query.field import (
        ComparableField,
        NullableOrdinalField,
        OrdinalField,
    )


T = TypeVar("T")

"""Conditions themselves, in the format <field> <operator> <value>

Example:
ImageSampleField.file_name == "img1.jpg",
becomes StringField(file_name) == "img1.jpg",
becomes StringFieldExpression(field=StringField(file_name), operator="==", value="img1.jpg")
becomes SQLQuery.where(...)
"""
ComparisonOperator = Literal["==", "!="]
OrdinalOperator = Literal[">", "<", "==", ">=", "<=", "!="]


@dataclass
class OrdinalFieldExpression(MatchExpression, Generic[T]):
    """Generic expression for ordinal field comparisons."""

    field: OrdinalField[T] | NullableOrdinalField[T]
    operator: OrdinalOperator
    value: T

    def get(self) -> ColumnElement[bool]:
        """Return the SQLAlchemy expression for this ordinal field expression."""
        table_property = self.field.get_sqlmodel_field()
        operations: dict[
            OrdinalOperator,
            Callable[[Mapped[T] | Mapped[T | None], T | ColumnElement[float]], ColumnElement[bool]],
        ] = {
            "<": lambda tp, v: tp < v,
            "<=": lambda tp, v: tp <= v,
            ">": lambda tp, v: tp > v,
            ">=": lambda tp, v: tp >= v,
            "==": lambda tp, v: tp == v,
            "!=": lambda tp, v: tp != v,
        }
        # DuckDB stores FLOAT columns at single precision but binds Python floats as DOUBLE.
        # Compare at the column's precision so inclusive bounds include the stored value.
        column_type = table_property.__clause_element__().type
        if isinstance(column_type, Float) and isinstance(self.value, float):
            return operations[self.operator](table_property, cast(self.value, column_type))
        return operations[self.operator](table_property, self.value)


NumericalFieldExpression = OrdinalFieldExpression[float | int]
DatetimeFieldExpression = OrdinalFieldExpression[datetime]


@dataclass
class ComparableFieldExpression(MatchExpression, Generic[T]):
    """Expression for field comparisons."""

    field: ComparableField[T]
    operator: ComparisonOperator
    value: T

    def get(self) -> ColumnElement[bool]:
        """Return the SQLAlchemy expression for this string field expression."""
        table_property = self.field.get_sqlmodel_field()
        operations: dict[ComparisonOperator, Callable[[Mapped[T], T], ColumnElement[bool]]] = {
            "==": lambda tp, v: tp == v,
            "!=": lambda tp, v: tp != v,
        }
        return operations[self.operator](table_property, self.value)
