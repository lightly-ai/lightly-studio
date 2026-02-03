"""Dummy LightlyTrain training operator for object detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.examples.coco_plugins_demo import lightly_train_inference_operator
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.parameter import BaseParameter, IntParameter, StringParameter
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

DEFAULT_INPUT_TAG = "labeled"
DEFAULT_MODEL_NAME = lightly_train_inference_operator.DEFAULT_MODEL_NAME
DEFAULT_EPOCHS = 50

PARAM_INPUT_TAG = "input_tag"
PARAM_MODEL_NAME = "model_name"
PARAM_EPOCHS = "epochs"


@dataclass
class LightlyTrainObjectDetectionTrainingOperator(BaseOperator):
    """Dummy operator that reports a cached training run."""

    name: str = "LightlyTrain object detection training"
    description: str = "Runs training for labeled images (dummy operator)."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            StringParameter(
                name=PARAM_MODEL_NAME,
                required=True,
                default=DEFAULT_MODEL_NAME,
                description="LightlyTrain model name to train.",
            ),
            StringParameter(
                name=PARAM_INPUT_TAG,
                required=True,
                default=DEFAULT_INPUT_TAG,
                description="Tag of samples to train on.",
            ),
            IntParameter(
                name=PARAM_EPOCHS,
                required=True,
                default=DEFAULT_EPOCHS,
                description="Number of epochs to report for training.",
            ),
        ]

    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters."""
        model_name = str(parameters.get(PARAM_MODEL_NAME, DEFAULT_MODEL_NAME))
        checkpoint_name = model_name
        input_tag = str(parameters.get(PARAM_INPUT_TAG, DEFAULT_INPUT_TAG))
        epochs = int(parameters.get(PARAM_EPOCHS, DEFAULT_EPOCHS))

        input_tag_entry = tag_resolver.get_by_name(
            session=session,
            tag_name=input_tag,
            collection_id=collection_id,
        )
        if input_tag_entry is None:
            return OperatorResult(
                success=True,
                message=(
                    f"No samples found for tag '{input_tag}'. "
                    f"Using cached checkpoint '{checkpoint_name}'."
                ),
            )

        samples_result = image_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
            filters=ImageFilter(
                sample_filter=SampleFilter(tag_ids=[input_tag_entry.tag_id]),
            ),
        )
        sample_count = samples_result.total_count

        return OperatorResult(
            success=True,
            message=(
                f"Training already completed on {sample_count} samples for "
                f"'{model_name}' ({epochs} epochs). Using cached checkpoint "
                f"'{checkpoint_name}'."
            ),
        )
