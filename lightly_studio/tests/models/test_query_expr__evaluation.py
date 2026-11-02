"""Validation and serialization of evaluation query contracts."""

import pytest
from pydantic import ValidationError

from lightly_studio.models.query_expr import EvaluationMetricComparisonExpr


@pytest.mark.parametrize("operator", ["==", "!=", "<", "<=", ">", ">="])
@pytest.mark.parametrize("value", [0, -2, 0.5])
def test_evaluation_metric_comparison(operator: str, value: int | float) -> None:
    metric = EvaluationMetricComparisonExpr.model_validate(
        {"metric_name": "custom metric", "operator": operator, "value": value}
    )
    assert type(metric.value) is type(value)
    assert EvaluationMetricComparisonExpr.model_validate_json(metric.model_dump_json()) == metric


@pytest.mark.parametrize("value", [True, False, "1", None, [], {}, float("inf"), float("nan")])
def test_evaluation_metric_comparison__invalid_value(value: object) -> None:
    with pytest.raises(ValidationError):
        EvaluationMetricComparisonExpr.model_validate(
            {"metric_name": "iou", "operator": ">", "value": value}
        )
