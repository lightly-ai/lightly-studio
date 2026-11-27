from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.evaluation_task import (
    ClassificationEvaluationConfig,
    EvaluationTask,
    SemanticSegmentationEvaluationConfig,
)


class TestEvaluationTask:
    def test_validate_config_for_task_type__json_round_trip(self) -> None:
        task = EvaluationTask(
            task_type=EvaluationTaskType.SEMANTIC_SEGMENTATION,
            name="run",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
            config=SemanticSegmentationEvaluationConfig(),
        )

        assert EvaluationTask.model_validate_json(task.model_dump_json()) == task

    @pytest.mark.parametrize("task_type", [EvaluationTaskType.SEMANTIC_SEGMENTATION, "unknown"])
    def test_validate_config_for_task_type__mismatch(self, task_type: Any) -> None:
        with pytest.raises(ValidationError):
            EvaluationTask(
                task_type=task_type,
                name="run",
                gt_annotation_source="gt",
                pred_annotation_source="pred",
                config=ClassificationEvaluationConfig(),
            )
