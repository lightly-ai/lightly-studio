"""Placeholder LightlyTrain training operator for object detection.

TODO(Malte, 02/2026): Replace placeholder with full LightlyTrain integration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from lightly_studio.examples.coco_plugins_demo import lightly_train_inference_operator
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.parameter import BaseParameter, IntParameter, StringParameter
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

DEFAULT_MODEL_NAME = lightly_train_inference_operator.DEFAULT_MODEL_NAME
DEFAULT_EPOCHS = 50

PARAM_MODEL_NAME = "model_name"
PARAM_EPOCHS = "epochs"


@dataclass
class LightlyTrainObjectDetectionTrainingOperator(BaseOperator):
    """Placeholder operator that reports a cached training run."""

    name: str = "LightlyTrain object detection training"
    description: str = "Runs training for labeled images."

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
            IntParameter(
                name=PARAM_EPOCHS,
                required=True,
                default=DEFAULT_EPOCHS,
                description="Number of epochs to report for training.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.IMAGE]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters."""
        collection_id = context.collection_id
        model_name = str(parameters.get(PARAM_MODEL_NAME, DEFAULT_MODEL_NAME))
        checkpoint_name = model_name
        epochs = int(parameters.get(PARAM_EPOCHS, DEFAULT_EPOCHS))

        time.sleep(3)

        context_filter = None
        if context.context_filter:
            if isinstance(context.context_filter, SampleFilter):
                context_filter = ImageFilter(sample_filter=context.context_filter)
            elif isinstance(context.context_filter, ImageFilter):
                context_filter = context.context_filter

        samples_result = image_resolver.get_all_by_collection_id(
            session=session, collection_id=collection_id, filters=context_filter
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
