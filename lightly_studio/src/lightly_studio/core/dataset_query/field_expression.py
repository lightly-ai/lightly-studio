"""Field expressions for building specific query conditions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

import numpy as np
from sqlalchemy import ColumnElement, Float, cast
from sqlalchemy.orm import InstrumentedAttribute, Mapped

from lightly_studio.core.dataset_query.match_expression import MatchExpression

if TYPE_CHECKING:
    from lightly_studio.core.dataset_query.field import (
        ComparableField,
        NullableOrdinalField,
        OrdinalField,
    )


T = TypeVar("T")
_MAX_FLOAT32 = float(np.finfo(np.float32).max)

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
        if (
            isinstance(self.value, float)
            and abs(self.value) <= _MAX_FLOAT32
            and (self.value == 0 or np.float32(self.value) != 0)
            and isinstance(table_property, InstrumentedAttribute)
            and isinstance(table_property.type, Float)
        ):
            return operations[self.operator](table_property, cast(self.value, table_property.type))
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
