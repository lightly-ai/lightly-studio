"""LightlyStudio operators for training, monitoring and deploying a detector.

The operators show up in the LightlyStudio menu under "Plugins". They run inside the
HTTP request, so each one starts background work and returns right away instead of
holding the UI while a model trains.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from lightly_studio.examples.camera_plugins_demo import dataset_bridge, demo_app, training
from lightly_studio.examples.camera_plugins_demo.demo_app import CameraDemo
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.parameter import (
    BaseParameter,
    FloatParameter,
    IntParameter,
    StringParameter,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

logger = logging.getLogger(__name__)

PARAM_MODEL = "model"
PARAM_STEPS = "steps"
PARAM_BATCH_SIZE = "batch_size"
PARAM_ANNOTATION_SOURCE = "annotation_source"
PARAM_VAL_FRACTION = "val_fraction"
PARAM_THRESHOLD = "score_threshold"


@dataclass
class TrainDetectorOperator(BaseOperator):
    """Trains an object detector with LightlyTrain on the images of the current view."""

    demo: CameraDemo
    name: str = "Train object detector (LightlyTrain)"
    description: str = (
        "Exports the annotations of the current view and fine-tunes a LightlyTrain "
        "object detection model on them."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        settings = self.demo.settings
        return [
            StringParameter(
                name=PARAM_MODEL,
                default=settings.default_model,
                description="LightlyTrain model to fine-tune.",
            ),
            IntParameter(
                name=PARAM_STEPS,
                default=settings.default_steps,
                description="Training steps. 60 steps take about 4 minutes on a laptop CPU.",
            ),
            IntParameter(
                name=PARAM_BATCH_SIZE,
                default=settings.default_batch_size,
                description="Images per step.",
            ),
            StringParameter(
                name=PARAM_ANNOTATION_SOURCE,
                default=demo_app.DEFAULT_ANNOTATION_SOURCE,
                description="Annotation source that holds the drawn bounding boxes.",
            ),
            FloatParameter(
                name=PARAM_VAL_FRACTION,
                default=0.2,
                description="Share of labeled images kept for validation.",
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
        """Export the current view and start a training run in the background."""
        if self.demo.trainings.is_running():
            return OperatorResult(success=False, message="A training run is already in progress.")

        model = str(parameters.get(PARAM_MODEL) or self.demo.settings.default_model)
        steps = _as_int(parameters.get(PARAM_STEPS), self.demo.settings.default_steps)
        batch_size = _as_int(
            parameters.get(PARAM_BATCH_SIZE), self.demo.settings.default_batch_size
        )
        annotation_source = str(
            parameters.get(PARAM_ANNOTATION_SOURCE) or demo_app.DEFAULT_ANNOTATION_SOURCE
        )
        val_fraction = _as_float(parameters.get(PARAM_VAL_FRACTION), 0.2)

        run_name = self.demo.trainings.next_run_name()
        run_dir = self.demo.trainings.run_dir(run_name=run_name)
        try:
            export = dataset_bridge.export_training_data(
                session=session,
                request=dataset_bridge.ExportRequest(
                    collection_id=context.collection_id,
                    image_filter=_as_image_filter(context=context),
                    annotation_source=annotation_source,
                    val_fraction=val_fraction,
                    output_dir=run_dir / "data",
                ),
            )
        except ValueError as exc:
            return OperatorResult(success=False, message=str(exc))

        state = self.demo.trainings.start(
            config=training.TrainingConfig(
                run_name=run_name,
                model=model,
                steps=steps,
                batch_size=batch_size,
                image_size=self.demo.settings.default_image_size,
                accelerator=demo_app.resolve_accelerator(),
                precision="32-true",
                num_workers=4,
                train_sample_ids=export.train_sample_ids,
                val_sample_ids=export.val_sample_ids,
                annotation_source=annotation_source,
            )
        )
        state.class_names = export.class_names
        skipped = (
            f" Skipped {export.skipped_count} images without annotations."
            if export.skipped_count
            else ""
        )
        return OperatorResult(
            success=True,
            message=(
                f"Started {run_name}: {model}, {steps} steps on {len(export.train_sample_ids)} "
                f"images ({len(export.val_sample_ids)} for validation), classes: "
                f"{', '.join(export.class_names)}.{skipped} Follow the progress at "
                f"{self.demo.station_url} and check back here for the Eval tab."
            ),
        )


@dataclass
class TrainingStatusOperator(BaseOperator):
    """Reports the progress of the training runs."""

    demo: CameraDemo
    name: str = "Training status"
    description: str = "Shows the progress and the metrics of the training runs."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.IMAGE, OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Return one line per training run."""
        del session, context, parameters
        states = self.demo.trainings.states()
        if not states:
            return OperatorResult(
                success=True,
                message="No training runs yet. Label some images and run 'Train object detector'.",
            )
        lines = []
        for state in states[:5]:
            if state.status == training.STATUS_RUNNING:
                loss = f", loss {state.loss:.2f}" if state.loss is not None else ""
                lines.append(f"{state.run_name}: step {state.step}/{state.steps}{loss}")
            else:
                metrics = ", ".join(f"{k} {v:.3f}" for k, v in sorted(state.metrics.items()))
                lines.append(
                    f"{state.run_name}: {state.status}. {metrics or state.message} "
                    f"{state.evaluation}".strip()
                )
        return OperatorResult(success=True, message=" | ".join(lines))


@dataclass
class DeployModelOperator(BaseOperator):
    """Runs a trained model on the live camera feed."""

    demo: CameraDemo
    name: str = "Deploy model to camera"
    description: str = (
        "Runs a trained model on the live camera feed and sends detections to MQTT "
        "and to the custom Python script."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            StringParameter(
                name=PARAM_MODEL,
                default="latest",
                description=(
                    "Training run name, 'latest' for the newest run, or a LightlyTrain model name."
                ),
            ),
            FloatParameter(
                name=PARAM_THRESHOLD,
                default=self.demo.settings.default_threshold,
                description="Minimum score for a detection.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.IMAGE, OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Start the model on the camera feed."""
        del session, context
        model = str(parameters.get(PARAM_MODEL) or "latest")
        threshold = _as_float(parameters.get(PARAM_THRESHOLD), self.demo.settings.default_threshold)
        try:
            message = self.demo.deploy(model=model, threshold=threshold)
        except ValueError as exc:
            return OperatorResult(success=False, message=str(exc))
        return OperatorResult(success=True, message=message)


@dataclass
class StopDeploymentOperator(BaseOperator):
    """Takes the model off the camera feed."""

    demo: CameraDemo
    name: str = "Stop camera deployment"
    description: str = "Stops the model that runs on the live camera feed."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.IMAGE, OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Stop the live model."""
        del session, context, parameters
        self.demo.stop_deployment()
        return OperatorResult(success=True, message="The camera feed runs without a model again.")


@dataclass
class BookmarkFrameOperator(BaseOperator):
    """Saves the current camera frame from inside LightlyStudio."""

    demo: CameraDemo
    name: str = "Bookmark current camera frame"
    description: str = "Adds the frame the camera shows right now to this dataset."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            StringParameter(
                name="tag",
                default=demo_app.BOOKMARK_TAG,
                description="Tag to assign to the new image.",
            )
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.IMAGE, OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Save the current frame as an image sample."""
        del session, context
        tag = str(parameters.get("tag") or "").strip()
        try:
            file_name = self.demo.bookmark(tags=[tag] if tag else [])
        except RuntimeError as exc:
            return OperatorResult(success=False, message=str(exc))
        return OperatorResult(success=True, message=f"Bookmarked {file_name}.")


def build_operators(demo: CameraDemo) -> list[BaseOperator]:
    """Return every operator of the camera demo."""
    return [
        TrainDetectorOperator(demo=demo),
        TrainingStatusOperator(demo=demo),
        DeployModelOperator(demo=demo),
        StopDeploymentOperator(demo=demo),
        BookmarkFrameOperator(demo=demo),
    ]


def _as_image_filter(context: ExecutionContext) -> ImageFilter | None:
    context_filter = context.context_filter
    if isinstance(context_filter, SampleFilter):
        return ImageFilter(sample_filter=context_filter)
    if isinstance(context_filter, ImageFilter):
        return context_filter
    return None


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
