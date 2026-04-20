from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from lightly_studio.query_language import (
    QueryTree,
)


def test_query_tree_accepts_valid_image_and_annotation_nodes() -> None:
    tree = QueryTree.model_validate(
        {
            "root": {
                "type": "and",
                "children": [
                    {
                        "type": "integer_field_comparison",
                        "field": "width",
                        "operator": ">=",
                        "value": 128,
                    },
                    {
                        "type": "classification_annotation_query",
                        "criteria": [
                            {
                                "type": "annotation_label_comparison",
                                "field": "label",
                                "operator": "==",
                                "value": "cat",
                            }
                        ],
                    },
                ],
            }
        }
    )

    assert tree.root.type == "and"


def test_query_tree_rejects_wrong_value_type_for_image_width() -> None:
    with pytest.raises(ValidationError):
        QueryTree.model_validate(
            {
                "root": {
                    "type": "integer_field_comparison",
                    "field": "width",
                    "operator": "==",
                    "value": "123",
                }
            }
        )


def test_query_tree_rejects_wrong_operator_for_video_duration() -> None:
    with pytest.raises(ValidationError):
        QueryTree.model_validate(
            {
                "root": {
                    "type": "equality_float_field_comparison",
                    "field": "duration_s",
                    "operator": ">=",
                    "value": 3.5,
                }
            }
        )


def test_query_tree_rejects_numeric_classification_criteria() -> None:
    with pytest.raises(ValidationError):
        QueryTree.model_validate(
            {
                "root": {
                    "type": "classification_annotation_query",
                    "criteria": [
                        {
                            "type": "annotation_geometry_comparison",
                            "field": "width",
                            "operator": ">=",
                            "value": 0.5,
                        }
                    ],
                }
            }
        )


def test_query_tree_parses_image_datetime_values() -> None:
    tree = QueryTree.model_validate(
        {
            "root": {
                "type": "datetime_field_comparison",
                "field": "created_at",
                "operator": ">=",
                "value": "2026-01-01T00:00:00Z",
            }
        }
    )

    assert tree.root.value == datetime(2026, 1, 1, tzinfo=timezone.utc)
