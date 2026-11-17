"""Validate video-only expressions before translating them to SQL."""

from lightly_studio.errors import QueryExprError
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    FieldRef,
    MatchExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalFloatExpr,
    OrExpr,
    SegmentationMaskMatchExpr,
    StringExpr,
    VideoEventMatchExpr,
)


def validate(expr: MatchExpr, scope: str | None) -> None:
    """Check event placement and fields, including boolean descendants."""
    field = getattr(expr, "field", None)
    if isinstance(expr, (AndExpr, OrExpr)):
        for child in expr.children:
            validate(expr=child, scope=scope)
    elif isinstance(expr, NotExpr):
        validate(expr=expr.child, scope=scope)
    elif scope == "event":
        _validate_event_field(expr=expr)
    elif isinstance(expr, VideoEventMatchExpr):
        if scope != "video":
            raise QueryExprError("Event queries require a video collection.")
        validate(expr=expr.subexpr, scope="event")
    elif isinstance(
        expr, (ClassificationMatchExpr, ObjectDetectionMatchExpr, SegmentationMaskMatchExpr)
    ):
        validate(expr=expr.subexpr, scope="annotation")
    elif isinstance(field, FieldRef) and field.table == "event":
        raise QueryExprError("Event fields require an event query.")


def _validate_event_field(expr: MatchExpr) -> None:
    fields = (
        {"class_name", "source"}
        if isinstance(expr, StringExpr)
        else {"confidence", "start_time_s", "end_time_s"}
    )
    if not isinstance(expr, (StringExpr, OrdinalFloatExpr)):
        raise QueryExprError("Event criteria must compare event fields.")
    if expr.field.table != "event" or expr.field.name not in fields:
        raise QueryExprError("Unknown event field.")
