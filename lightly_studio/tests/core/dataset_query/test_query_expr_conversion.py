from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pytest

from lightly_studio.core.dataset_query import query_expr_conversion, query_translation
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field_expression import OrdinalFieldExpression
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import (
    OrderByExpression,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.core.dataset_query.query_expr_conversion import UnsupportedQueryError
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import FieldRef
from lightly_studio.models.sample_query import SortKey
from lightly_studio.models.sort_direction import SortDirection

_DATE = datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_to_query_expr() -> None:
    match = AND(
        ImageSampleField.width > 100,
        OR(ImageSampleField.file_name == "a.png", NOT(ImageSampleField.tags.contains("cat"))),
    )

    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=SampleType.IMAGE
    )

    assert query_expr.model_dump(mode="json") == {
        "match_expr": {
            "type": "and",
            "children": [
                {
                    "type": "integer_expr",
                    "field": {"table": "image", "name": "width"},
                    "operator": ">",
                    "value": 100,
                },
                {
                    "type": "or",
                    "children": [
                        {
                            "type": "string_expr",
                            "field": {"table": "image", "name": "file_name"},
                            "operator": "==",
                            "value": "a.png",
                        },
                        {
                            "type": "not",
                            "child": {
                                "type": "tags_contains_expr",
                                "field": {"table": "image", "name": "tags"},
                                "tag_name": "cat",
                            },
                        },
                    ],
                },
            ],
        }
    }


@pytest.mark.parametrize(
    ("sample_type", "match"),
    [
        (SampleType.IMAGE, ImageSampleField.file_name == "a.png"),
        (SampleType.IMAGE, ImageSampleField.file_path_abs != "/a.png"),
        (SampleType.IMAGE, ImageSampleField.width > 100),
        (SampleType.IMAGE, ImageSampleField.height <= 100),
        (SampleType.IMAGE, ImageSampleField.created_at >= _DATE),
        (SampleType.IMAGE, ImageSampleField.tags.contains("cat")),
        (SampleType.IMAGE, ImageSampleField.metadata["weather"] == "sunny"),
        (SampleType.IMAGE, ImageSampleField.metadata["odometry.acc[1]"] < 1.5),
        (SampleType.IMAGE, ImageSampleField.metadata["night"] != True),  # noqa: E712
        (SampleType.VIDEO, VideoSampleField.file_name != "a.mp4"),
        (SampleType.VIDEO, VideoSampleField.file_path_abs == "/a.mp4"),
        (SampleType.VIDEO, VideoSampleField.width < 100),
        (SampleType.VIDEO, VideoSampleField.height == 100),
        (SampleType.VIDEO, VideoSampleField.fps > 29.97),
        (SampleType.VIDEO, VideoSampleField.fps == 30),
        (SampleType.VIDEO, VideoSampleField.duration_s <= 2.5),
        (SampleType.VIDEO, VideoSampleField.duration_s != 3),
        (SampleType.VIDEO, VideoSampleField.created_at > _DATE),
        (SampleType.VIDEO, VideoSampleField.tags.contains("cat")),
        (SampleType.VIDEO_FRAME, VideoFrameSampleField.tags.contains("cat")),
        (SampleType.VIDEO, VideoSampleField.metadata["weather"] == "sunny"),
        (SampleType.VIDEO, OR(AND(VideoSampleField.fps < 10), NOT(VideoSampleField.width > 1))),
    ],
)
def test_to_query_expr__same_sql(sample_type: SampleType, match: MatchExpression) -> None:
    query_expr = query_expr_conversion.to_query_expr(
        match_expression=match, sample_type=sample_type
    )

    translated = query_translation.to_match_expression(
        expr=query_expr.match_expr, sample_type=sample_type
    )

    assert _sql(match=translated) == _sql(match=match)


@pytest.mark.parametrize(
    ("sample_type", "match"),
    [
        (SampleType.IMAGE, ImageSampleField.width > 1.5),
        (
            SampleType.IMAGE,
            OrdinalFieldExpression[Any](field=ImageSampleField.created_at, operator=">", value=0),
        ),
        (SampleType.VIDEO, VideoSampleField.fps > float("inf")),
        (
            SampleType.VIDEO,
            OrdinalFieldExpression[Any](
                field=VideoSampleField.fps, operator=">", value=np.float32("inf")
            ),
        ),
        (SampleType.IMAGE, VideoSampleField.width > 100),
        (SampleType.VIDEO, ImageSampleField.width > 100),
        (SampleType.IMAGE, AND()),
    ],
)
def test_to_query_expr__not_supported(sample_type: SampleType, match: MatchExpression) -> None:
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_query_expr(match_expression=match, sample_type=sample_type)


def test_to_sort_keys() -> None:
    order_by = [
        OrderByField(ImageSampleField.width).desc(),
        OrderByField(ImageSampleField.created_at),
    ]

    sort_keys = query_expr_conversion.to_sort_keys(order_by=order_by, sample_type=SampleType.IMAGE)

    assert sort_keys == [
        SortKey(field=FieldRef(table="image", name="width"), direction=SortDirection.desc),
        SortKey(field=FieldRef(table="image", name="created_at"), direction=SortDirection.asc),
    ]


@pytest.mark.parametrize(
    "order_by",
    [OrderByMetadataField(field_name="weather"), OrderByField(VideoSampleField.fps)],
)
def test_to_sort_keys__not_supported(order_by: OrderByExpression) -> None:
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_sort_keys(order_by=[order_by], sample_type=SampleType.IMAGE)


def _sql(match: MatchExpression) -> str:
    return str(match.get().compile(compile_kwargs={"literal_binds": True}))
