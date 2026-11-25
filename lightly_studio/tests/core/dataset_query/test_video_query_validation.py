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
    MetadataComparisonExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    QueryExpr,
    SampleEvaluationMatchExpr,
    StringExpr,
    TagsContainsExpr,
    VideoEventMatchExpr,
    VideoFrameMatchExpr,
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
        VideoEventMatchExpr(subexpr=ClassificationMatchExpr()),
    )
    for expr in invalid_expressions:
        with pytest.raises(QueryExprError):
            query_translation.to_match_expression(expr=expr, sample_type=SampleType.VIDEO)
    image_filter = ImageFilter(
        sample_filter=SampleFilter(query_expr=QueryExpr(match_expr=NotExpr(child=event)))
    )
    with pytest.raises(QueryExprError, match="video collection"):
        image_filter.apply(query=select(ImageTable).join(ImageTable.sample))


@pytest.mark.parametrize("table", ["image", "video", "event", "video_frame"])
def test_invalid_frame_fields(table: str) -> None:
    field = OrdinalFloatExpr(
        field=FieldRef(table=table, name="width"), operator=OrdinalComparisonOperator.GT, value=1
    )
    for criterion in (field, ObjectDetectionMatchExpr(subexpr=field)):
        expr = VideoFrameMatchExpr(subexpr=NotExpr(child=criterion))
        with pytest.raises(QueryExprError):
            query_translation.to_match_expression(expr=expr, sample_type=SampleType.VIDEO)


def test_frame_scope() -> None:
    field = OrdinalFloatExpr(
        field=FieldRef(table="video_frame", name="frame_timestamp_s"),
        operator=OrdinalComparisonOperator.GT,
        value=1,
    )
    frame = VideoFrameMatchExpr(subexpr=field)
    for criterion in (
        frame,
        VideoEventMatchExpr(subexpr=field),
        SampleEvaluationMatchExpr(run_name="run"),
        MetadataComparisonExpr(path="speed", operator=OrdinalComparisonOperator.GT, value=1),
        ObjectDetectionMatchExpr(subexpr=frame),
    ):
        with pytest.raises(QueryExprError):
            query_translation.to_match_expression(
                expr=VideoFrameMatchExpr(subexpr=criterion), sample_type=SampleType.VIDEO
            )
    with pytest.raises(QueryExprError, match="video collection"):
        query_translation.to_match_expression(
            expr=NotExpr(child=frame), sample_type=SampleType.IMAGE
        )
    with pytest.raises(QueryExprError, match="frame query"):
        query_translation.to_match_expression(expr=field, sample_type=SampleType.VIDEO)


@pytest.mark.parametrize("sample_type", [None, SampleType.IMAGE, SampleType.VIDEO])
def test_frame_fields_outside_frame_scope(sample_type: SampleType | None) -> None:
    expr = TagsContainsExpr(field=FieldRef(table="video_frame", name="tags"), tag_name="blurry")
    with pytest.raises(QueryExprError, match="frame query"):
        query_translation.to_match_expression(expr=expr, sample_type=sample_type)


def test_frame_scope__video_tags() -> None:
    tags = TagsContainsExpr(field=FieldRef(table="video", name="tags"), tag_name="reviewed")
    with pytest.raises(QueryExprError, match="frame fields"):
        query_translation.to_match_expression(
            expr=VideoFrameMatchExpr(subexpr=tags), sample_type=SampleType.VIDEO
        )


def test_video_frame_scope__event_field() -> None:
    field = FieldRef(table="event", name="class_name")
    expr = StringExpr(field=field, operator=EqualityComparisonOperator.EQ, value="run")
    with pytest.raises(QueryExprError, match="event or frame query"):
        query_translation.to_match_expression(expr=expr, sample_type=SampleType.VIDEO_FRAME)
