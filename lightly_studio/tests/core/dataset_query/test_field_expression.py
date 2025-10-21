from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

import pytest
from sqlmodel import Session, select

from lightly_studio.core.dataset_query.field_expression import (
    DatetimeFieldExpression,
    NumericalFieldExpression,
    OrdinalOperator,
    StringFieldExpression,
    StringOperator,
)
from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_dataset, create_sample


class TestNumericalFieldExpression:
    def test_apply__less(self) -> None:
        query = select(SampleTable)

        expr = NumericalFieldExpression(field=SampleField.height, operator="<", value=10)

        returned_query = query.where(expr.get())

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "where samples.height < 10" in sql

    def test_apply__greater_equal(self) -> None:
        query = select(SampleTable)

        expr = NumericalFieldExpression(field=SampleField.height, operator=">=", value=100)

        returned_query = query.where(expr.get())

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "where samples.height >= 100" in sql

    @pytest.mark.parametrize(
        ("operator", "test_value", "expected_match"),
        [
            # Test with height=100 sample
            ("<", 99, False),
            ("<", 100, False),
            ("<", 101, True),
            ("<=", 99, False),
            ("<=", 100, True),
            ("<=", 101, True),
            (">", 99, True),
            (">", 100, False),
            (">", 101, False),
            (">=", 99, True),
            (">=", 100, True),
            (">=", 101, False),
            ("==", 99, False),
            ("==", 100, True),
            ("==", 101, False),
            ("!=", 99, True),
            ("!=", 100, False),
            ("!=", 101, True),
        ],
    )
    def test_operators__real_db(
        self, test_db: Session, operator: OrdinalOperator, test_value: float, expected_match: bool
    ) -> None:
        """Test numerical operators against a real database with a sample of height=100."""
        # Arrange
        dataset = create_dataset(session=test_db)
        sample = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/test.jpg",
            width=200,
            height=100,  # Test sample has height 100
        )

        # Act
        expr = NumericalFieldExpression(
            field=SampleField.height, operator=operator, value=test_value
        )
        query = select(SampleTable).where(SampleTable.dataset_id == dataset.dataset_id)
        result_query = query.where(expr.get())
        results = test_db.exec(result_query).all()

        # Assert
        if expected_match:
            assert len(results) == 1
            assert results[0].sample_id == sample.sample_id
        else:
            assert len(results) == 0


class TestDatetimeFieldExpression:
    def test_apply__greater_than(self) -> None:
        query = select(SampleTable)
        test_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        expr = DatetimeFieldExpression(
            field=SampleField.created_at, operator=">", value=test_datetime
        )

        returned_query = query.where(expr.get())

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "where samples.created_at > '2023-01-01 12:00:00+00:00'" in sql

    def test_apply__less_than_or_equal(self) -> None:
        query = select(SampleTable)
        test_datetime = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

        expr = DatetimeFieldExpression(
            field=SampleField.created_at, operator="<=", value=test_datetime
        )

        returned_query = query.where(expr.get())

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "where samples.created_at <= '2024-06-15 10:30:00+00:00'" in sql


class TestStringFieldExpression:
    def test_apply__equal(self) -> None:
        query = select(SampleTable)

        expr = StringFieldExpression(field=SampleField.file_name, operator="==", value="test.jpg")

        returned_query = query.where(expr.get())

        sql = str(returned_query.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "where samples.file_name = 'test.jpg'" in sql

    @pytest.mark.parametrize(
        ("operator", "test_value", "expected_match"),
        [
            ("==", "test.jpg", True),
            ("==", "other.jpg", False),
            ("==", "TEST.JPG", False),  # Case sensitive
            ("==", "", False),
            ("!=", "test.jpg", False),
            ("!=", "other.jpg", True),
            ("!=", "TEST.JPG", True),  # Case sensitive
            ("!=", "", True),
        ],
    )
    def test_operators__real_db(
        self, test_db: Session, operator: str, test_value: str, expected_match: bool
    ) -> None:
        """Test string operators against a real database with a sample named 'test.jpg'."""
        # Arrange
        dataset = create_dataset(session=test_db)
        sample = create_sample(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/test.jpg",
            width=200,
            height=100,
        )
        # The create_sample helper creates file_name from file_path_abs

        # Act
        expr = StringFieldExpression(
            field=SampleField.file_name, operator=cast(StringOperator, operator), value=test_value
        )
        query = select(SampleTable).where(SampleTable.dataset_id == dataset.dataset_id)
        result_query = query.where(expr.get())
        results = test_db.exec(result_query).all()

        # Assert
        if expected_match:
            assert len(results) == 1
            assert results[0].sample_id == sample.sample_id
        else:
            assert len(results) == 0
