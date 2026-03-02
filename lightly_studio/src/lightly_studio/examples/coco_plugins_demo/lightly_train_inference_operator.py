"""LightlyTrain inference operator for object detection auto-labeling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import lightly_train  # type: ignore[import-not-found]
from lightly_train._commands import predict_task_helpers  # type: ignore[import-not-found]
from PIL import Image
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import OperatorScope
from lightly_studio.plugins.parameter import BaseParameter, FloatParameter, StringParameter
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

DEFAULT_INPUT_TAG = "unlabeled"
DEFAULT_MODEL_NAME = "dinov3/convnext-tiny-ltdetr-coco"
DEFAULT_SCORE_THRESHOLD = 0.5

PARAM_INPUT_TAG = "input_tag"
PARAM_MODEL_NAME = "model_name"
PARAM_SCORE_THRESHOLD = "score_threshold"


@dataclass
class LightlyTrainObjectDetectionInferenceOperator(BaseOperator):
    """Runs LightlyTrain object detection inference to auto-label images."""

    name: str = "LightlyTrain object detection inference"
    description: str = "Runs object detection inference and adds annotations to unlabeled images."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            StringParameter(
                name=PARAM_MODEL_NAME,
                required=True,
                default=DEFAULT_MODEL_NAME,
                description="LightlyTrain model name to load.",
            ),
            FloatParameter(
                name=PARAM_SCORE_THRESHOLD,
                required=True,
                default=DEFAULT_SCORE_THRESHOLD,
                description="Minimum score for keeping a prediction.",
            ),
            StringParameter(
                name=PARAM_INPUT_TAG,
                required=True,
                default=DEFAULT_INPUT_TAG,
                description="Tag of samples to auto-label.",
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
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters."""
        model_name = str(parameters.get(PARAM_MODEL_NAME, DEFAULT_MODEL_NAME))
        score_threshold = float(parameters.get(PARAM_SCORE_THRESHOLD, DEFAULT_SCORE_THRESHOLD))
        input_tag = str(parameters.get(PARAM_INPUT_TAG, DEFAULT_INPUT_TAG))

        if score_threshold < 0.0 or score_threshold > 1.0:
            return OperatorResult(
                success=False,
                message="score_threshold must be between 0 and 1",
            )

        input_tag_entry = tag_resolver.get_by_name(
            session=session,
            tag_name=input_tag,
            collection_id=collection_id,
        )
        if input_tag_entry is None:
            return OperatorResult(
                success=False,
                message=f"Tag '{input_tag}' not found.",
            )

        model = lightly_train.load_model(model=model_name)
        label_map = _get_or_create_label_map(
            session=session,
            dataset_id=collection_id,
            class_map=model.classes,
        )

        samples_result = image_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
            filters=ImageFilter(
                sample_filter=SampleFilter(tag_ids=[input_tag_entry.tag_id]),
            ),
        )
        samples = list(samples_result.samples)
        if not samples:
            return OperatorResult(
                success=True,
                message=f"No samples found for tag '{input_tag}'.",
            )

        annotations_to_create: list[AnnotationCreate] = []
        processed_sample_count = 0
        for image_entry in samples:
            processed_sample_count += 1

            with Image.open(fp=image_entry.file_path_abs) as opened_image:
                image_for_prediction = opened_image.convert("RGB")
                predictions = model.predict(
                    image_for_prediction,
                    threshold=score_threshold,
                )
                coco_entries = predict_task_helpers.prepare_coco_entries(
                    predictions=predictions,
                    image_size=(image_entry.width, image_entry.height),
                )
            for entry in coco_entries:
                annotation_label_id = label_map.get(entry["category_id"])
                if annotation_label_id is None:
                    continue
                # TODO(Malte, 02/2026): Create predictions instead of annotations.
                annotations_to_create.append(
                    AnnotationCreate(
                        annotation_label_id=annotation_label_id,
                        annotation_type=AnnotationType.OBJECT_DETECTION,
                        parent_sample_id=image_entry.sample_id,
                        x=round(entry["bbox"][0]),
                        y=round(entry["bbox"][1]),
                        width=round(entry["bbox"][2]),
                        height=round(entry["bbox"][3]),
                        confidence=entry["score"],
                    )
                )

        if annotations_to_create:
            annotation_resolver.create_many(
                session=session,
                parent_collection_id=collection_id,
                annotations=annotations_to_create,
            )

        return OperatorResult(
            success=True,
            message=f"Auto-labeled {processed_sample_count} samples.",
        )


def _get_or_create_label_map(
    *,
    session: Session,
    dataset_id: UUID,
    class_map: dict[int, str],
) -> dict[int, UUID]:
    """Ensure labels exist for all class names and return {category_id: label_id}."""
    label_map: dict[int, UUID] = {}
    for category_id, label_name in class_map.items():
        label = annotation_label_resolver.get_by_label_name(
            session=session,
            dataset_id=dataset_id,
            label_name=label_name,
        )
        if label is None:
            label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id,
                    annotation_label_name=label_name,
                ),
            )
        label_map[category_id] = label.annotation_label_id
    return label_map
