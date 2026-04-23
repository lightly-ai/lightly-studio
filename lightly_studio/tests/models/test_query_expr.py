"""A surface-level smoke test for the QueryExpr model for documentation purposes."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    DatetimeExpr,
    NotExpr,
    QueryExpr,
    StringExpr,
)


class TestQueryExpr:
    def test_model_validate__and_with_image_and_annotation_nodes(self) -> None:
        """Compose an AND of a leaf image filter and a nested annotation match."""
        tree = QueryExpr.model_validate(
            {
                "match_expr": {
                    "type": "and",
                    "children": [
                        {
                            "type": "integer_expr",
                            "field": {"table": "image", "name": "width"},
                            "operator": ">=",
                            "value": 128,
                        },
                        {
                            "type": "classification_match_expr",
                            "subexpr": {
                                "type": "string_expr",
                                "field": {
                                    "table": "classification",
                                    "name": "label",
                                },
                                "operator": "==",
                                "value": "cat",
                            },
                        },
                    ],
                }
            }
        )
        assert isinstance(tree.match_expr, AndExpr)
        classification_child = tree.match_expr.children[1]
        assert isinstance(classification_child, ClassificationMatchExpr)
        assert isinstance(classification_child.subexpr, StringExpr)

    def test_model_validate__not_wraps_single_child(self) -> None:
        """NOT negates a single leaf expression."""
        tree = QueryExpr.model_validate(
            {
                "match_expr": {
                    "type": "not",
                    "child": {
                        "type": "tags_contains_expr",
                        "field": {"table": "image", "name": "tags"},
                        "tag_name": "reviewed",
                    },
                }
            }
        )
        assert isinstance(tree.match_expr, NotExpr)

    def test_model_validate__datetime_value_is_parsed(self) -> None:
        """ISO-8601 strings are parsed into datetime objects."""
        tree = QueryExpr.model_validate(
            {
                "match_expr": {
                    "type": "datetime_expr",
                    "field": {"table": "image", "name": "created_at"},
                    "operator": ">=",
                    "value": "2026-01-01T00:00:00Z",
                }
            }
        )
        assert isinstance(tree.match_expr, DatetimeExpr)
        assert tree.match_expr.value == datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_model_validate__rejects_wrong_value_type(self) -> None:
        """String value is rejected where an integer is expected."""
        with pytest.raises(ValidationError):
            QueryExpr.model_validate(
                {
                    "match_expr": {
                        "type": "integer_expr",
                        "field": {"table": "image", "name": "width"},
                        "operator": "==",
                        "value": "not_a_number",
                    }
                }
            )

    def test_model_validate__rejects_ordinal_operator_on_equality_field(self) -> None:
        """Equality-only float fields reject ordinal operators like >=."""
        with pytest.raises(ValidationError):
            QueryExpr.model_validate(
                {
                    "match_expr": {
                        "type": "equality_float_expr",
                        "field": {"table": "video", "name": "duration_s"},
                        "operator": ">=",
                        "value": 3.5,
                    }
                }
            )
