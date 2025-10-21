"""Field expressions for building specific query conditions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Generic, Literal, TypeVar, Union

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Mapped

from lightly_studio.core.dataset_query.match_expression import MatchExpression

if TYPE_CHECKING:
    from lightly_studio.core.dataset_query.field import (
        OrdinalField,
        StringField,
    )


T = TypeVar("T")

"""Conditions themselves, in the format <field> <operator> <value>

Example:
SampleField.file_name == "img1.jpg",
becomes StringField(file_name) == "img1.jpg",
becomes StringFieldExpression(field=StringField(file_name), operator="==", value="img1.jpg")
becomes SQLQuery.where(...)
"""
StringOperator = Literal["==", "!="]
OrdinalOperator = Literal[">", "<", "==", ">=", "<=", "!="]


@dataclass
class OrdinalFieldExpression(MatchExpression, Generic[T]):
    """Generic expression for ordinal field comparisons."""

    field: OrdinalField[T]
    operator: OrdinalOperator
    value: T

    def get(self) -> ColumnElement[bool]:
        """Return the SQLAlchemy expression for this ordinal field expression."""
        table_property = self.field.get_sqlmodel_field()
        operations: dict[
            OrdinalOperator,
            Callable[[Mapped[T], T], ColumnElement[bool]],
        ] = {
            "<": lambda tp, v: tp < v,
            "<=": lambda tp, v: tp <= v,
            ">": lambda tp, v: tp > v,
            ">=": lambda tp, v: tp >= v,
            "==": lambda tp, v: tp == v,
            "!=": lambda tp, v: tp != v,
        }
        return operations[self.operator](table_property, self.value)


NumericalFieldExpression = OrdinalFieldExpression[Union[float, int]]
DatetimeFieldExpression = OrdinalFieldExpression[datetime]


@dataclass
class StringFieldExpression(MatchExpression):
    """Expression for string field comparisons."""

    field: StringField
    operator: StringOperator
    value: str

    def get(self) -> ColumnElement[bool]:
        """Return the SQLAlchemy expression for this string field expression."""
        table_property = self.field.get_sqlmodel_field()
        operations: dict[StringOperator, Callable[[Mapped[str], str], ColumnElement[bool]]] = {
            "==": lambda tp, v: tp == v,
            "!=": lambda tp, v: tp != v,
        }
        return operations[self.operator](table_property, self.value)
