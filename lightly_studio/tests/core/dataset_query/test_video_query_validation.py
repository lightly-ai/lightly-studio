import pytest
from sqlmodel import select

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.errors import QueryExprError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.query_expr import (
    ClassificationMatchExpr,
    EqualityComparisonOperator,
    FieldRef,
    NotExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    QueryExpr,
    StringExpr,
    VideoEventMatchExpr,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


@pytest.mark.parametrize(
    ("table", "name"), [("image", "width"), ("event", "width"), ("event", "class_name")]
)
def test_invalid_event_fields(table: str, name: str) -> None:
    expr = VideoEventMatchExpr(
        subexpr=OrdinalFloatExpr(
            field=FieldRef(table=table, name=name),
            operator=OrdinalComparisonOperator.GT,
            value=1,
        )
    )
    with pytest.raises(QueryExprError, match="event field"):
        query_translation.to_match_expression(expr=expr, sample_type=SampleType.VIDEO)


def test_event_scope() -> None:
    field = StringExpr(
        field=FieldRef(table="event", name="class_name"),
        operator=EqualityComparisonOperator.EQ,
        value="run",
    )
    event = VideoEventMatchExpr(subexpr=field)
    invalid_expressions = (
        field,
        ClassificationMatchExpr(subexpr=event),
        VideoEventMatchExpr(subexpr=event),
    )
    for expr in invalid_expressions:
        with pytest.raises(QueryExprError):
            query_translation.to_match_expression(expr=expr, sample_type=SampleType.VIDEO)
    image_filter = ImageFilter(
        sample_filter=SampleFilter(query_expr=QueryExpr(match_expr=NotExpr(child=event)))
    )
    with pytest.raises(QueryExprError, match="video collection"):
        image_filter.apply(query=select(ImageTable).join(ImageTable.sample))
