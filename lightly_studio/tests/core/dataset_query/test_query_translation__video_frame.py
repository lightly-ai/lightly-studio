"""Tests for translating video and video frame fields of the query format."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.video_frame_query import VideoFrameQuery
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    DatetimeExpr,
    EqualityComparisonOperator,
    EqualityFloatExpr,
    FieldRef,
    IntegerExpr,
    MatchExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    StringExpr,
    TagsContainsExpr,
    VideoFrameMatchExpr,
)
from lightly_studio.models.sort_direction import SortDirection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames

_FRAME_TAGS = TagsContainsExpr(field=FieldRef(table="video_frame", name="tags"), tag_name="blurry")
_PARENT_VIDEO = VideoFrameSampleField.parent_video
_EQ = EqualityComparisonOperator.EQ
_GT = OrdinalComparisonOperator.GT


@pytest.mark.parametrize("name", ["frame_number", "frame_timestamp_pts", "rotation_deg"])
def test_to_match_expression__video_frame_integer_fields(name: str) -> None:
    field = FieldRef(table="video_frame", name=name)
    expr = IntegerExpr(field=field, operator=OrdinalComparisonOperator.GT, value=90)
    _assert_frame_translation(expr=expr, expected=getattr(VideoFrameSampleField, name) > 90)


def test_to_match_expression__video_frame_tags() -> None:
    _assert_frame_translation(
        expr=_FRAME_TAGS, expected=VideoFrameSampleField.tags.contains("blurry")
    )


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (
            StringExpr(
                field=FieldRef(table="parent_video", name="file_name"), operator=_EQ, value="a.mp4"
            ),
            _PARENT_VIDEO.file_name == "a.mp4",
        ),
        (
            StringExpr(
                field=FieldRef(table="parent_video", name="file_path_abs"),
                operator=_EQ,
                value="/a.mp4",
            ),
            _PARENT_VIDEO.file_path_abs == "/a.mp4",
        ),
        (
            IntegerExpr(
                field=FieldRef(table="parent_video", name="width"), operator=_GT, value=640
            ),
            _PARENT_VIDEO.width > 640,
        ),
        (
            IntegerExpr(
                field=FieldRef(table="parent_video", name="height"), operator=_GT, value=480
            ),
            _PARENT_VIDEO.height > 480,
        ),
        (
            OrdinalFloatExpr(
                field=FieldRef(table="parent_video", name="fps"), operator=_GT, value=2.5
            ),
            _PARENT_VIDEO.fps > 2.5,
        ),
        (
            EqualityFloatExpr(
                field=FieldRef(table="parent_video", name="fps"), operator=_EQ, value=3.0
            ),
            _PARENT_VIDEO.fps == 3.0,
        ),
        (
            EqualityFloatExpr(
                field=FieldRef(table="parent_video", name="duration_s"), operator=_EQ, value=1.0
            ),
            _PARENT_VIDEO.duration_s == 1.0,
        ),
        (
            OrdinalFloatExpr(
                field=FieldRef(table="parent_video", name="duration_s"), operator=_GT, value=0.5
            ),
            _PARENT_VIDEO.duration_s > 0.5,
        ),
        (
            TagsContainsExpr(
                field=FieldRef(table="parent_video", name="tags"), tag_name="reviewed"
            ),
            _PARENT_VIDEO.tags.contains("reviewed"),
        ),
    ],
)
def test_to_match_expression__parent_video_fields(
    expr: MatchExpr, expected: MatchExpression
) -> None:
    _assert_frame_translation(expr=expr, expected=expected)


def test_to_match_expression__video_created_at() -> None:
    created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    field = FieldRef(table="video", name="created_at")
    expr = DatetimeExpr(field=field, operator=OrdinalComparisonOperator.GT, value=created_at)
    translated = query_translation.to_match_expression(expr=expr, sample_type=SampleType.VIDEO)
    assert _to_sql(translated) == _to_sql(VideoSampleField.created_at > created_at)


@pytest.mark.parametrize(
    "name", ["frame_number", "frame_timestamp_s", "frame_timestamp_pts", "rotation_deg"]
)
def test_sort_to_order_by__video_frame_fields(name: str) -> None:
    order_by = query_translation.sort_to_order_by(
        key=("video_frame", name), direction=SortDirection.desc
    )
    assert isinstance(order_by, OrderByField)
    assert order_by.field is getattr(VideoFrameSampleField, name)
    assert not order_by.ascending


@pytest.mark.usefixtures("patch_collection")
def test_to_match_expression__video_frame_tags_in_database() -> None:
    dataset = VideoDataset.create(name="ds")
    for path, fps in (("/data/a.mp4", 3.0), ("/data/b.mp4", 2.0)):
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path=path, duration_s=1.0, fps=fps),
        )
    for frame in dataset.frames():
        if frame.frame_number == 2:
            frame.add_tag("blurry")

    frame_match = query_translation.to_match_expression(
        expr=_FRAME_TAGS, sample_type=SampleType.VIDEO_FRAME
    )
    frames = dataset.frames().match(frame_match).to_list()
    assert [(f.parent_video.file_path_abs, f.frame_number) for f in frames] == [("/data/a.mp4", 2)]

    video_match = query_translation.to_match_expression(
        expr=VideoFrameMatchExpr(subexpr=_FRAME_TAGS), sample_type=SampleType.VIDEO
    )
    videos = dataset.query().match(video_match).to_list()
    assert [video.file_path_abs for video in videos] == ["/data/a.mp4"]


@pytest.mark.usefixtures("patch_collection")
def test_to_match_expression__parent_video_tags_in_database() -> None:
    dataset = VideoDataset.create(name="ds")
    for path in ("/data/a.mp4", "/data/b.mp4"):
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path=path, duration_s=1.0, fps=2.0),
        )
    for video in dataset.query():
        if video.file_path_abs == "/data/b.mp4":
            video.add_tag("reviewed")

    parent_tags = TagsContainsExpr(
        field=FieldRef(table="parent_video", name="tags"), tag_name="reviewed"
    )
    parent_match = query_translation.to_match_expression(
        expr=parent_tags, sample_type=SampleType.VIDEO_FRAME
    )
    frames = dataset.frames().match(parent_match).to_list()
    assert [(f.parent_video.file_path_abs, f.frame_number) for f in frames] == [
        ("/data/b.mp4", 0),
        ("/data/b.mp4", 1),
    ]


def _assert_frame_translation(expr: MatchExpr, expected: MatchExpression) -> None:
    """Check the translation in the frame grid and inside a frame query of the video grid."""
    frame_grid = query_translation.to_match_expression(
        expr=expr, sample_type=SampleType.VIDEO_FRAME
    )
    assert _to_sql(frame_grid) == _to_sql(expected)
    video_grid = query_translation.to_match_expression(
        expr=VideoFrameMatchExpr(subexpr=expr), sample_type=SampleType.VIDEO
    )
    assert _to_sql(video_grid) == _to_sql(VideoFrameQuery(expected))


def _to_sql(expr: MatchExpression) -> str:
    return str(expr.get().compile(compile_kwargs={"literal_binds": True}))
