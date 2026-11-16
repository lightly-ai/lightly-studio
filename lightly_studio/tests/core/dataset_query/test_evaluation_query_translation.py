"""Evaluation payloads translate to the existing Python query expressions."""

import pytest

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.annotation_evaluation_query import AnnotationMetricQuery
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.evaluation_metric_expression import (
    EvaluationMetricMatchExpression,
)
from lightly_studio.core.dataset_query.sample_evaluation_query import SampleEvaluationQuery
from lightly_studio.models.query_expr import QueryExpr


def test_to_match_expression__sample_boolean_criteria() -> None:
    metric = {
        "type": "evaluation_metric_comparison_expr",
        "metric_name": "fp",
        "operator": ">",
        "value": 2,
    }
    payload = {
        "match_expr": {
            "type": "sample_evaluation_match_expr",
            "run_name": "run1",
            "criteria": [
                {
                    "type": "and",
                    "children": [{"type": "or", "children": [{"type": "not", "child": metric}]}],
                }
            ],
        }
    }
    actual = query_translation.to_match_expression(
        expr=QueryExpr.model_validate(payload).match_expr
    )
    expected = SampleEvaluationQuery(
        "run1",
        AND(OR(NOT(EvaluationMetricMatchExpression(metric_name="fp", operator=">", value=2)))),
    )
    assert str(actual.get()) == str(expected.get())
    assert actual.get().compile().params == expected.get().compile().params


@pytest.mark.parametrize("kind", ["confusion", "false_positive", "false_negative"])
def test_to_match_expression__annotation(kind: str) -> None:
    payload: dict[str, object] = {"type": f"{kind}_match_expr", "run_name": "run1"}
    if kind != "false_positive":
        payload["ground_truth"] = "car"
    if kind != "false_negative":
        payload["prediction"] = "truck"
    if kind == "confusion":
        payload["criteria"] = [
            {
                "type": "evaluation_metric_comparison_expr",
                "metric_name": "iou",
                "operator": ">",
                "value": 0.5,
            }
        ]
    actual = query_translation.to_match_expression(
        expr=QueryExpr.model_validate({"match_expr": payload}).match_expr
    )
    assert isinstance(actual, AnnotationMetricQuery)
    assert actual.run_name == "run1"
    assert actual.match_kind == kind
    assert actual.gt_label_name == (None if kind == "false_positive" else "car")
    assert actual.pred_label_name == (None if kind == "false_negative" else "truck")
    assert [(c.metric_name, c.operator, c.value) for c in actual.criteria] == (
        [("iou", ">", 0.5)] if kind == "confusion" else []
    )
