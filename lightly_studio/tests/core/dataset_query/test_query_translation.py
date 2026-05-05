"""Tests for translating query expression models into dataset-query expressions."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.errors import QueryExprError
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    DatetimeExpr,
    EqualityComparisonOperator,
    EqualityFloatExpr,
    FieldRef,
    IntegerExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    OrExpr,
    SegmentationMaskMatchExpr,
    StringExpr,
    TagsContainsExpr,
)


def test_to_match_expression__string_eq() -> None:
    expr = StringExpr(
        field=FieldRef(table="image", name="file_name"),
        operator=EqualityComparisonOperator.EQ,
        value="cat.jpg",
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "image.file_name = 'cat.jpg'" in sql


def test_to_match_expression__string_neq() -> None:
    expr = StringExpr(
        field=FieldRef(table="image", name="file_name"),
        operator=EqualityComparisonOperator.NEQ,
        value="dog.jpg",
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "image.file_name != 'dog.jpg'" in sql


def test_to_match_expression__string_unknown_field() -> None:
    expr = StringExpr(
        field=FieldRef(table="image", name="nonexistent"),
        operator=EqualityComparisonOperator.EQ,
        value="x",
    )
    with pytest.raises(QueryExprError, match="Unknown string field"):
        query_translation.to_match_expression(expr)


@pytest.mark.parametrize(
    ("operator", "expected_op"),
    [
        (OrdinalComparisonOperator.LT, "<"),
        (OrdinalComparisonOperator.LTE, "<="),
        (OrdinalComparisonOperator.GT, ">"),
        (OrdinalComparisonOperator.GTE, ">="),
        (OrdinalComparisonOperator.EQ, "="),
        (OrdinalComparisonOperator.NEQ, "!="),
    ],
)
def test_to_match_expression__integer_operators(
    operator: OrdinalComparisonOperator, expected_op: str
) -> None:
    expr = IntegerExpr(
        field=FieldRef(table="image", name="width"),
        operator=operator,
        value=800,
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert f"image.width {expected_op} 800" in sql


def test_to_match_expression__integer_unknown_field() -> None:
    expr = IntegerExpr(
        field=FieldRef(table="image", name="depth"),
        operator=OrdinalComparisonOperator.EQ,
        value=3,
    )
    with pytest.raises(QueryExprError, match="Unknown integer field"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__integer_wrong_type_for_valid_field() -> None:
    expr = IntegerExpr(
        field=FieldRef(table="classification", name="label"),
        operator=OrdinalComparisonOperator.EQ,
        value=3,
    )
    with pytest.raises(QueryExprError, match="Unknown integer field"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__datetime_gt() -> None:
    dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    expr = DatetimeExpr(
        field=FieldRef(table="image", name="created_at"),
        operator=OrdinalComparisonOperator.GT,
        value=dt,
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "image.created_at >" in sql
    assert "2024-01-15" in sql


def test_to_match_expression__datetime_unknown_field() -> None:
    expr = DatetimeExpr(
        field=FieldRef(table="image", name="updated_at"),
        operator=OrdinalComparisonOperator.EQ,
        value=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(QueryExprError, match="Unknown datetime field"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__ordinal_float_lt() -> None:
    expr = OrdinalFloatExpr(
        field=FieldRef(table="video", name="fps"),
        operator=OrdinalComparisonOperator.LT,
        value=30.0,
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "video.fps < 30.0" in sql


def test_to_match_expression__ordinal_float_unknown_field() -> None:
    expr = OrdinalFloatExpr(
        field=FieldRef(table="video", name="bitrate"),
        operator=OrdinalComparisonOperator.EQ,
        value=1.0,
    )
    with pytest.raises(QueryExprError, match="Unknown ordinal float field"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__equality_float_eq() -> None:
    expr = EqualityFloatExpr(
        field=FieldRef(table="video", name="duration_s"),
        operator=EqualityComparisonOperator.EQ,
        value=10.5,
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "video.duration_s = 10.5" in sql


def test_to_match_expression__equality_float_neq() -> None:
    expr = EqualityFloatExpr(
        field=FieldRef(table="video", name="duration_s"),
        operator=EqualityComparisonOperator.NEQ,
        value=0,
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "video.duration_s != 0" in sql


def test_to_match_expression__equality_float_unknown_field() -> None:
    expr = EqualityFloatExpr(
        field=FieldRef(table="image", name="size_mb"),
        operator=EqualityComparisonOperator.EQ,
        value=1.0,
    )
    with pytest.raises(QueryExprError, match="Unknown equality float field"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__tags_contains() -> None:
    expr = TagsContainsExpr(
        field=FieldRef(table="image", name="tags"),
        tag_name="reviewed",
    )
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "exists" in sql
    assert "tag.name = 'reviewed'" in sql


def test_to_match_expression__tags_unknown_field() -> None:
    expr = TagsContainsExpr(
        field=FieldRef(table="image", name="labels"),
        tag_name="x",
    )
    with pytest.raises(QueryExprError, match="Unknown tags field"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__classification_match() -> None:
    subexpr = StringExpr(
        field=FieldRef(table="classification", name="label"),
        operator=EqualityComparisonOperator.EQ,
        value="cat",
    )
    expr = ClassificationMatchExpr(subexpr=subexpr)
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "exists" in sql
    assert "annotation_type = 'classification'" in sql
    assert "annotation_label_name = 'cat'" in sql


def test_to_match_expression__object_detection_match() -> None:
    subexpr = IntegerExpr(
        field=FieldRef(table="object_detection", name="width"),
        operator=OrdinalComparisonOperator.GT,
        value=50,
    )
    expr = ObjectDetectionMatchExpr(subexpr=subexpr)
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "exists" in sql
    assert "annotation_type = 'object_detection'" in sql
    assert "object_detection_annotation.width > 50" in sql


def test_to_match_expression__segmentation_mask_match() -> None:
    subexpr = StringExpr(
        field=FieldRef(table="segmentation_mask", name="label"),
        operator=EqualityComparisonOperator.EQ,
        value="person",
    )
    expr = SegmentationMaskMatchExpr(subexpr=subexpr)
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "exists" in sql
    assert "annotation_type = 'segmentation_mask'" in sql
    assert "annotation_label_name = 'person'" in sql


def test_to_match_expression__and() -> None:
    child_a = IntegerExpr(
        field=FieldRef(table="image", name="width"),
        operator=OrdinalComparisonOperator.GT,
        value=100,
    )
    child_b = IntegerExpr(
        field=FieldRef(table="image", name="height"),
        operator=OrdinalComparisonOperator.LT,
        value=500,
    )
    expr = AndExpr(children=[child_a, child_b])
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "image.width > 100" in sql
    assert "image.height < 500" in sql
    assert " and " in sql


def test_to_match_expression__or() -> None:
    child_a = StringExpr(
        field=FieldRef(table="image", name="file_name"),
        operator=EqualityComparisonOperator.EQ,
        value="a.jpg",
    )
    child_b = StringExpr(
        field=FieldRef(table="image", name="file_name"),
        operator=EqualityComparisonOperator.EQ,
        value="b.jpg",
    )
    expr = OrExpr(children=[child_a, child_b])
    sql = _to_sql(query_translation.to_match_expression(expr))
    assert "file_name = 'a.jpg'" in sql
    assert "file_name = 'b.jpg'" in sql
    assert " or " in sql


def test_to_match_expression__not() -> None:
    child = IntegerExpr(
        field=FieldRef(table="image", name="width"),
        operator=OrdinalComparisonOperator.LT,
        value=100,
    )
    expr = NotExpr(child=child)
    sql = _to_sql(query_translation.to_match_expression(expr))
    # NOT(width < 100) is compiled as width >= 100 by SQLAlchemy.
    assert "image.width >= 100" in sql


def test_to_match_expression__nested_and_or() -> None:
    """AND containing an OR should produce correct SQL."""
    or_expr = OrExpr(
        children=[
            IntegerExpr(
                field=FieldRef(table="image", name="width"),
                operator=OrdinalComparisonOperator.EQ,
                value=100,
            ),
            IntegerExpr(
                field=FieldRef(table="image", name="width"),
                operator=OrdinalComparisonOperator.EQ,
                value=200,
            ),
        ]
    )
    and_expr = AndExpr(
        children=[
            IntegerExpr(
                field=FieldRef(table="image", name="height"),
                operator=OrdinalComparisonOperator.GT,
                value=50,
            ),
            or_expr,
        ]
    )
    sql = _to_sql(query_translation.to_match_expression(and_expr))
    assert "image.height > 50" in sql
    assert "image.width = 100" in sql
    assert "image.width = 200" in sql
    assert " and " in sql
    assert " or " in sql


def _to_sql(expr: MatchExpression) -> str:
    """Compile a MatchExpression to a lowercase SQL string for assertions."""
    return str(expr.get().compile(compile_kwargs={"literal_binds": True})).lower()
