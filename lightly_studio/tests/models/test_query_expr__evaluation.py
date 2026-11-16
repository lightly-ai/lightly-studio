"""Validation and serialization of evaluation query contracts."""

import pytest
from pydantic import ValidationError

from lightly_studio.models.query_expr import EvaluationMetricComparisonExpr, QueryExpr


class TestEvaluationMetricComparisonExpr:
    @pytest.mark.parametrize("operator", ["==", "!=", "<", "<=", ">", ">="])
    @pytest.mark.parametrize("value", [0, -2, 0.5])
    def test_model_validate(self, operator: str, value: int | float) -> None:
        metric = EvaluationMetricComparisonExpr.model_validate(
            {"metric_name": "custom metric", "operator": operator, "value": value}
        )
        assert type(metric.value) is type(value)
        assert (
            EvaluationMetricComparisonExpr.model_validate_json(metric.model_dump_json()) == metric
        )

    @pytest.mark.parametrize("value", [True, False, "1", None, [], {}, float("inf"), float("nan")])
    def test_model_validate__invalid_value(self, value: object) -> None:
        with pytest.raises(ValidationError):
            EvaluationMetricComparisonExpr.model_validate(
                {"metric_name": "iou", "operator": ">", "value": value}
            )


class TestQueryExpr:
    @pytest.mark.parametrize(
        "expression",
        [
            {
                "type": "sample_evaluation_match_expr",
                "run_name": "run1",
                "criteria": [
                    {
                        "type": "and",
                        "children": [
                            {
                                "type": "or",
                                "children": [
                                    {
                                        "type": "not",
                                        "child": {
                                            "type": "evaluation_metric_comparison_expr",
                                            "metric_name": "fp",
                                            "operator": "==",
                                            "value": 0,
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            {
                "type": "confusion_match_expr",
                "run_name": "run1",
                "ground_truth": "car",
                "prediction": "truck",
                "criteria": [
                    {
                        "type": "evaluation_metric_comparison_expr",
                        "metric_name": "iou",
                        "operator": ">",
                        "value": 0.5,
                    }
                ],
            },
            {"type": "false_positive_match_expr", "run_name": "run1", "prediction": "truck"},
            {"type": "false_negative_match_expr", "run_name": "run1", "ground_truth": "car"},
        ],
    )
    def test_model_validate__evaluation_round_trip(self, expression: dict[str, object]) -> None:
        payload = {"match_expr": {"type": "not", "child": expression}}
        query = QueryExpr.model_validate(payload)
        assert query.model_dump(mode="json") == payload
        assert QueryExpr.model_validate_json(query.model_dump_json()) == query

    @pytest.mark.parametrize(
        "expression",
        [
            {
                "type": "evaluation_metric_comparison_expr",
                "metric_name": "fp",
                "operator": "==",
                "value": 0,
            },
            {"type": "sample_evaluation_match_expr"},
            {"type": "sample_evaluation_match_expr", "run_name": 1},
            {"type": "false_positive_match_expr", "run_name": "run1"},
            {"type": "false_negative_match_expr", "run_name": "run1"},
            {"type": "confusion_match_expr", "run_name": "run1", "ground_truth": "car"},
            {
                "type": "false_positive_match_expr",
                "run_name": "run1",
                "prediction": "car",
                "criteria": [],
            },
            {
                "type": "false_negative_match_expr",
                "run_name": "run1",
                "ground_truth": "car",
                "prediction": "truck",
            },
            {
                "type": "confusion_match_expr",
                "run_name": "run1",
                "ground_truth": "car",
                "prediction": "truck",
                "criteria": [{"type": "and", "children": []}],
            },
            {
                "type": "sample_evaluation_match_expr",
                "run_name": "run1",
                "criteria": [{"type": "or", "children": []}],
            },
            {
                "type": "sample_evaluation_match_expr",
                "run_name": "run1",
                "criteria": [
                    {"type": "false_positive_match_expr", "run_name": "run2", "prediction": "car"}
                ],
            },
            {
                "type": "sample_evaluation_match_expr",
                "run_name": "run1",
                "criteria": [
                    {
                        "type": "integer_expr",
                        "field": {"table": "image", "name": "width"},
                        "operator": ">",
                        "value": 1,
                    }
                ],
            },
        ],
    )
    def test_model_validate__invalid_evaluation(self, expression: dict[str, object]) -> None:
        with pytest.raises(ValidationError):
            QueryExpr.model_validate({"match_expr": expression})

    @pytest.mark.parametrize(
        "annotation_type",
        [
            "classification_match_expr",
            "object_detection_match_expr",
            "segmentation_mask_match_expr",
        ],
    )
    def test_model_validate__evaluation_inside_annotation(self, annotation_type: str) -> None:
        with pytest.raises(ValidationError, match="cannot be nested inside annotation"):
            QueryExpr.model_validate(
                {
                    "match_expr": {
                        "type": annotation_type,
                        "subexpr": {
                            "type": "not",
                            "child": {
                                "type": "false_positive_match_expr",
                                "run_name": "run1",
                                "prediction": "car",
                            },
                        },
                    }
                }
            )

    def test_model_json_schema(self) -> None:
        schema = QueryExpr.model_json_schema()
        mapping = schema["properties"]["match_expr"]["discriminator"]["mapping"]
        assert mapping["sample_evaluation_match_expr"] == "#/$defs/SampleEvaluationMatchExpr"
        assert "evaluation_metric_comparison_expr" not in mapping
        assert schema["$defs"]["FalsePositiveMatchExpr"]["additionalProperties"] is False
