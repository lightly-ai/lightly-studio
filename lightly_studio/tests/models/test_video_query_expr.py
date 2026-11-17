import pytest

from lightly_studio.models.query_expr import (
    EqualityComparisonOperator,
    FieldRef,
    NotExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    QueryExpr,
    StringExpr,
    VideoEventMatchExpr,
)


@pytest.mark.parametrize(
    "name", ["class_name", "source", "confidence", "start_time_s", "end_time_s"]
)
def test_video_event_fields__round_trip(name: str) -> None:
    field = FieldRef(table="event", name=name)
    criterion = (
        StringExpr(field=field, operator=EqualityComparisonOperator.EQ, value="run")
        if name in {"class_name", "source"}
        else OrdinalFloatExpr(field=field, operator=OrdinalComparisonOperator.GTE, value=0.5)
    )
    query = QueryExpr(match_expr=VideoEventMatchExpr(subexpr=NotExpr(child=criterion)))
    restored = QueryExpr.model_validate_json(query.model_dump_json())
    assert restored == query
