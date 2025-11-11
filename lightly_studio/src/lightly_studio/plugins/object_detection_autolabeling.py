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
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter
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
            BoolParameter(name="test flag", required=True),
            StringParameter(name="test str", required=True),
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
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        dataset = dataset_resolver.get_by_id(session=session, dataset_id=dataset_id)
        if dataset is None:
            return OperatorResult(
                success=False,
                message=f"Dataset with id {dataset_id} not found.",
            )

        for sample in dataset.get_samples():
            image_path = sample.file_path_abs
            model = lightly_train.load_model(
                "dinov3/convnext-tiny-ltdetr-coco"
            )  # TODO: make model name a parameter
            preds = model.predict(image_path, threshold=0.6)  # type: ignore[call-arg] # TODO: make threshold a parameter
            with Image.open(image_path) as pil_image:
                entries = predict_task_helpers.prepare_coco_entries(
                    predictions=preds,
                    image_size=pil_image.size,
                )

            prediction_path = Path(image_path).parent.with_suffix(
                ".json"
            )  # TODO: make prediction path relative to dataset root
            predict_task_helpers.save_coco_json(
                entries=entries,
                coco_filepath=prediction_path,
            )

        return OperatorResult(
            success=bool(parameters.get("test flag")),
            message=str(parameters.get("test str")) + " " + str(session) + " " + str(dataset_id),
        )
