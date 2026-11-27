from __future__ import annotations

import pytest
from pydantic import ValidationError

from lightly_studio.models.query_expr import FieldRef
from lightly_studio.models.sample_query import EvaluationMetricSortKey, SampleQueryRequest, SortKey
from lightly_studio.models.sort_direction import SortDirection


class TestSampleQueryRequest:
    def test_validate_offset(self) -> None:
        assert SampleQueryRequest(offset=5).offset == 5
        assert SampleQueryRequest(cursor="abc").cursor == "abc"

    def test_validate_offset__with_cursor__raises(self) -> None:
        with pytest.raises(ValidationError, match="only on the first page"):
            SampleQueryRequest(cursor="abc", offset=5)

    @pytest.mark.parametrize("limit", [0, 1001])
    def test_limit__out_of_range__raises(self, limit: int) -> None:
        with pytest.raises(ValidationError):
            SampleQueryRequest(limit=limit)

    def test_sort(self) -> None:
        request = SampleQueryRequest.model_validate(
            {
                "sort": [
                    {"field": {"table": "image", "name": "width"}},
                    {"run_name": "run", "metric_name": "miou", "direction": "desc"},
                ]
            }
        )

        assert request.sort == [
            SortKey(field=FieldRef(table="image", name="width")),
            EvaluationMetricSortKey(
                run_name="run", metric_name="miou", direction=SortDirection.desc
            ),
        ]

    def test_sort__field_and_metric_in_one_key__raises(self) -> None:
        with pytest.raises(ValidationError):
            SampleQueryRequest.model_validate(
                {
                    "sort": [
                        {
                            "field": {"table": "image", "name": "width"},
                            "run_name": "run",
                            "metric_name": "miou",
                        }
                    ]
                }
            )
