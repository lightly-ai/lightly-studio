"""A surface-level smoke test for the QueryExpr model for documentation purposes."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    DatetimeExpr,
    MetadataComparisonExpr,
    NotExpr,
    OrdinalComparisonOperator,
    QueryExpr,
    StringExpr,
)


class TestMetadataComparisonExpr:
    @pytest.mark.parametrize("value", ["front", "1", True, False, 1, -2, 0.8, -5.5])
    @pytest.mark.parametrize("operator", list(OrdinalComparisonOperator))
    def test_model_validate(self, value: str | bool | int | float, operator: str) -> None:
        payload = {
            "match_expr": {
                "type": "metadata_comparison_expr",
                "path": "odometry.acc[1]",
                "operator": operator,
                "value": value,
            }
        }
        if isinstance(value, (str, bool)) and operator not in ("==", "!="):
            with pytest.raises(ValidationError, match="ordering comparisons require a number"):
                QueryExpr.model_validate(payload)
            return

        query = QueryExpr.model_validate(payload)
        assert isinstance(query.match_expr, MetadataComparisonExpr)
        assert type(query.match_expr.value) is type(value)
        assert query.model_dump(mode="json") == payload
        assert QueryExpr.model_validate_json(query.model_dump_json()) == query

    @pytest.mark.parametrize("value", [None, [], {}, float("nan"), float("inf"), -float("inf")])
    def test_model_validate__invalid_value(self, value: object) -> None:
        with pytest.raises(ValidationError):
            MetadataComparisonExpr.model_validate(
                {"path": "camera", "operator": "==", "value": value}
            )

    def test_model_validate__invalid_operator(self) -> None:
        with pytest.raises(ValidationError):
            MetadataComparisonExpr.model_validate(
                {"path": "camera", "operator": "IN", "value": "front"}
            )

    @pytest.mark.parametrize(
        "expression",
        [
            {
                "type": "and",
                "children": [
                    {
                        "type": "metadata_comparison_expr",
                        "path": "camera",
                        "operator": "==",
                        "value": "front",
                    }
                ],
            },
            {
                "type": "or",
                "children": [
                    {
                        "type": "metadata_comparison_expr",
                        "path": "reviewed",
                        "operator": "!=",
                        "value": False,
                    }
                ],
            },
            {
                "type": "not",
                "child": {
                    "type": "metadata_comparison_expr",
                    "path": "score",
                    "operator": ">=",
                    "value": 0.8,
                },
            },
        ],
    )
    def test_model_validate__boolean_composition(self, expression: dict[str, object]) -> None:
        query = QueryExpr.model_validate({"match_expr": expression})
        assert query.model_dump(mode="json") == {"match_expr": expression}
        assert QueryExpr.model_validate_json(query.model_dump_json()) == query


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
