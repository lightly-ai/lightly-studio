"""Validate video-only expressions before translating them to SQL."""

from lightly_studio.errors import QueryExprError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    FieldRef,
    IntegerExpr,
    MatchExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalFloatExpr,
    OrExpr,
    PolygonMatchExpr,
    SegmentationMaskMatchExpr,
    StringExpr,
    VideoEventMatchExpr,
    VideoFrameMatchExpr,
)

_FRAME_TABLES = frozenset({"video_frame", "parent_video"})


def validate(expr: MatchExpr, scope: str | None) -> None:
    """Check video expression placement and fields, including boolean descendants."""
    if isinstance(expr, (AndExpr, OrExpr)):
        for child in expr.children:
            validate(expr=child, scope=scope)
    elif isinstance(expr, NotExpr):
        validate(expr=expr.child, scope=scope)
    else:
        _validate_node(expr=expr, scope=scope)


def _validate_node(expr: MatchExpr, scope: str | None) -> None:
    field = getattr(expr, "field", None)
    if scope == "event":
        _validate_event_field(expr=expr)
    elif scope is not None and scope.startswith("frame:"):
        _validate_frame_annotation_field(expr=expr, table=scope.removeprefix("frame:"))
    elif isinstance(expr, (VideoEventMatchExpr, VideoFrameMatchExpr)):
        if scope != "video":
            raise QueryExprError("Event and frame queries require a video collection.")
        validate(
            expr=expr.subexpr, scope="event" if isinstance(expr, VideoEventMatchExpr) else "frame"
        )
    elif isinstance(
        expr,
        (
            ClassificationMatchExpr,
            ObjectDetectionMatchExpr,
            SegmentationMaskMatchExpr,
            PolygonMatchExpr,
        ),
    ):
        child_scope = (
            "frame:" + expr.type.removesuffix("_match_expr") if scope == "frame" else "annotation"
        )
        if expr.subexpr is not None:
            validate(expr=expr.subexpr, scope=child_scope)
    elif scope == "frame":
        if not _is_frame_field(field=field):
            raise QueryExprError("Frame criteria require annotation queries or frame fields.")
    else:
        _validate_video_field_scope(field=field, scope=scope)


def _validate_video_field_scope(field: object, scope: str | None) -> None:
    if scope == SampleType.VIDEO_FRAME.value and _is_frame_field(field=field):
        return
    if isinstance(field, FieldRef) and field.table in {"event", *_FRAME_TABLES}:
        raise QueryExprError("Video fields require their event or frame query.")


def _is_frame_field(field: object) -> bool:
    return isinstance(field, FieldRef) and field.table in _FRAME_TABLES


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


def _validate_frame_annotation_field(expr: MatchExpr, table: str) -> None:
    if (
        not isinstance(expr, (StringExpr, IntegerExpr, OrdinalFloatExpr))
        or expr.field.table != table
    ):
        raise QueryExprError(
            "Frame annotation criteria must compare fields of that annotation type."
        )
