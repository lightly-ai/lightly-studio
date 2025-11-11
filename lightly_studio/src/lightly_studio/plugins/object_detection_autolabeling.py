"""Operator to autolabel a dataset with an object detection model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import lightly_train
from lightly_train._commands import predict_task_helpers
from PIL import Image
from sqlmodel import Session

from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.parameter import BaseParameter, FloatParameter, StringParameter
from lightly_studio.resolvers import dataset_resolver


@dataclass
class ObjDetAutolabelingOperator(BaseOperator):
    """Operator to autolabel a dataset with an object detection model."""

    name: str = "object detection autolabeling operator"
    description: str = "used to autolabel a dataset with an object detection model"

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            StringParameter(name="model_name", required=True),
            FloatParameter(name="threshold", default=0.6),
        ]

    def execute(
        self,
        *,
        session: Session,
        dataset_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            dataset_id: ID of the dataset to operate on.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with the result of the operation.
        """
        dataset = dataset_resolver.get_by_id(session=session, dataset_id=dataset_id)
        if dataset is None:
            return OperatorResult(
                success=False,
                message=f"Object detection autolabeling failed: Dataset {dataset_id} not found.",
            )

        for sample in dataset.get_samples():
            image_path = Path(sample.file_path_abs)

            model = lightly_train.load_model(parameters.get("model_name"))  # type: ignore[arg-type]

            preds = model.predict(image_path, threshold=parameters.get("threshold"))  # type: ignore[call-arg]

            with Image.open(image_path) as pil_image:
                entries = predict_task_helpers.prepare_coco_entries(
                    predictions=preds,
                    image_size=pil_image.size,
                )
            prediction_path = image_path.with_suffix(".json")
            predict_task_helpers.save_coco_json(
                entries=entries,
                coco_filepath=prediction_path,
            )

        return OperatorResult(
            success=True,
            message=f"Object detection autolabeling completed successfully \
            for dataset {dataset_id} with model {parameters.get('model_name')}.",
        )
