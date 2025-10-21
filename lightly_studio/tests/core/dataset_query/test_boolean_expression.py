"""Tests for logical combination of SQLModel/SQLAlchemy expressions using MatchExpression."""

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field_expression import (
    NumericalFieldExpression,
)
from lightly_studio.core.dataset_query.sample_field import SampleField


class TestAndExpression:
    def test_init(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        b = NumericalFieldExpression(field=SampleField.height, operator=">", value=20)
        expr = AND(a, b)
        assert expr.terms == (a, b)

    def test_init__empty(self) -> None:
        expr = AND()
        assert expr.terms == ()

    def test_init__single(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        expr = AND(a)
        assert expr.terms == (a,)

    def test_get(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        b = NumericalFieldExpression(field=SampleField.height, operator=">", value=20)
        expr = AND(a, b)
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "samples.height < 10 and samples.height > 20"

    def test_get__single(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        expr = AND(a)
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "samples.height < 10"

    def test_get__empty(self) -> None:
        expr = AND()
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "true"


class TestOrExpression:
    def test_init(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        b = NumericalFieldExpression(field=SampleField.height, operator=">", value=20)
        expr = OR(a, b)
        assert expr.terms == (a, b)

    def test_init__empty(self) -> None:
        expr = OR()
        assert expr.terms == ()

    def test_init__single(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        expr = OR(a)
        assert expr.terms == (a,)

    def test_get(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        b = NumericalFieldExpression(field=SampleField.height, operator=">", value=20)
        expr = OR(a, b)
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "samples.height < 10 or samples.height > 20"

    def test_get__single(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        expr = OR(a)
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "samples.height < 10"

    def test_get__empty(self) -> None:
        expr = OR()
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "false"


class TestNotExpression:
    def test_init(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        expr = NOT(a)
        assert expr.term == a

    def test_get(self) -> None:
        a = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)
        expr = NOT(a)
        exprs = expr.get()
        sql = str(exprs.compile(compile_kwargs={"literal_binds": True})).lower()
        assert sql == "samples.height >= 10"
