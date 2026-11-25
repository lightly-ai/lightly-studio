from __future__ import annotations

import pytest

from lightly_studio.core.dataset_query import query_expr_conversion
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import (
    OrderByExpression,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.core.dataset_query.query_expr_conversion import UnsupportedQueryError
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.models.query_expr import FieldRef
from lightly_studio.models.sample_query import SortKey
from lightly_studio.models.sort_direction import SortDirection


def test_to_query_expr() -> None:
    match = AND(
        ImageSampleField.width > 100,
        OR(ImageSampleField.file_name == "a.png", NOT(ImageSampleField.tags.contains("cat"))),
    )

    query_expr = query_expr_conversion.to_query_expr(match_expression=match)

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
    "match",
    [
        ImageSampleField.metadata["weather"] == "sunny",
        ImageSampleField.width > 1.5,
        AND(),
    ],
)
def test_to_query_expr__not_supported(match: MatchExpression) -> None:
    with pytest.raises(UnsupportedQueryError):
        query_expr_conversion.to_query_expr(match_expression=match)


def test_to_sort_keys() -> None:
    order_by = [
        OrderByField(ImageSampleField.width).desc(),
        OrderByField(ImageSampleField.created_at),
    ]

    sort_keys = query_expr_conversion.to_sort_keys(order_by=order_by)

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
        query_expr_conversion.to_sort_keys(order_by=[order_by])
