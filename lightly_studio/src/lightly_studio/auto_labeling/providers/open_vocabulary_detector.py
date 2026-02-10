"""Open vocabulary object detection provider."""

from __future__ import annotations

import json
import random
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.auto_labeling.base_provider import (
    BaseAutoLabelingProvider,
    ProviderParameter,
    ProviderResult,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver


class OpenVocabularyDetectorProvider(BaseAutoLabelingProvider):
    """Provider for open vocabulary object detection (mock/placeholder API)."""

    @property
    def provider_id(self) -> str:
        return "open_vocabulary_detector"

    @property
    def name(self) -> str:
        return "Open Vocabulary Object Detector"

    @property
    def description(self) -> str:
        return "Detect objects using text prompts (custom API)"

    @property
    def parameters(self) -> list[ProviderParameter]:
        return [
            ProviderParameter(
                name="api_url",
                type="string",
                description="URL of inference server (e.g., http://localhost:8001/detect)",
                required=True,
            ),
            ProviderParameter(
                name="class_prompts",
                type="json",
                description='Class prompts as JSON: {"car": "a red car", "person": "walking person"}',
                required=True,
            ),
            ProviderParameter(
                name="tag_filter",
                type="tag_filter",
                description="Filter samples by tags",
                required=False,
            ),
            ProviderParameter(
                name="confidence_threshold",
                type="float",
                description="Minimum confidence for detections",
                default=0.5,
                required=False,
            ),
            ProviderParameter(
                name="result_tag_name",
                type="string",
                description="Name of tag to add to processed samples",
                default="ovd-detected",
                required=True,
            ),
        ]

    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> list[ProviderResult]:
        """Execute detection on filtered samples."""
        api_url = parameters["api_url"]
        class_prompts_raw = parameters["class_prompts"]

        # Parse class_prompts if it's a string
        if isinstance(class_prompts_raw, str):
            class_prompts = json.loads(class_prompts_raw)
        else:
            class_prompts = class_prompts_raw

        tag_filter = parameters.get("tag_filter")
        threshold = parameters.get("confidence_threshold", 0.5)

        # Convert tag name to UUID if provided
        tag_ids = None
        if tag_filter:
            tag = tag_resolver.get_by_name(
                session=session,
                collection_id=collection_id,
                tag_name=tag_filter,
            )
            if tag:
                tag_ids = [tag.tag_id]
                print(f"[DEBUG] OVD provider: Resolved tag '{tag_filter}' to UUID {tag.tag_id}")
            else:
                print(f"[DEBUG] OVD provider: Tag '{tag_filter}' not found")

        # Get samples
        samples = self._get_samples_by_filter(session, collection_id, tag_ids)

        results = []
        for sample in samples:
            try:
                detections = self._detect_objects(
                    api_url=api_url,
                    sample=sample,
                    class_prompts=class_prompts,
                    threshold=threshold,
                )

                # Filter detections to only include requested classes
                valid_class_names = set(class_prompts.keys())
                detections = [
                    det for det in detections
                    if det.get("class_name") in valid_class_names
                ]

                if not detections:
                    # No detections for this sample
                    results.append(
                        ProviderResult(
                            sample_id=sample.sample_id,
                            success=True,
                            data={"detections": []},
                        )
                    )
                    continue

                # Get image for dimensions
                from lightly_studio.models.image import ImageTable
                from lightly_studio.models.annotation.annotation_base import (
                    AnnotationCreate,
                    AnnotationType,
                )
                from lightly_studio.resolvers import (
                    annotation_resolver,
                    annotation_label_resolver,
                    collection_resolver,
                )
                from lightly_studio.models.annotation_label import AnnotationLabelCreate

                image = session.get(ImageTable, sample.sample_id)
                if not image:
                    raise ValueError(f"No image found for sample {sample.sample_id}")

                # Get dataset ID for annotation labels
                dataset = collection_resolver.get_dataset(session, collection_id)
                dataset_id = dataset.collection_id

                # Create annotations
                annotations = []
                for det in detections:
                    # Get or create annotation label
                    label = annotation_label_resolver.get_by_label_name(
                        session=session,
                        dataset_id=dataset_id,
                        label_name=det["class_name"],
                    )
                    if not label:
                        label = annotation_label_resolver.create(
                            session=session,
                            label=AnnotationLabelCreate(
                                dataset_id=dataset_id,
                                annotation_label_name=det["class_name"],
                            ),
                        )

                    # Convert normalized coordinates to pixels
                    x_px = int(det["bbox"][0] * image.width)
                    y_px = int(det["bbox"][1] * image.height)
                    width_px = int(det["bbox"][2] * image.width)
                    height_px = int(det["bbox"][3] * image.height)

                    annotations.append(
                        AnnotationCreate(
                            annotation_label_id=label.annotation_label_id,
                            annotation_type=AnnotationType.OBJECT_DETECTION,
                            parent_sample_id=sample.sample_id,
                            confidence=det.get("confidence"),
                            x=x_px,
                            y=y_px,
                            width=width_px,
                            height=height_px,
                        )
                    )

                # Bulk create annotations
                annotation_resolver.create_many(
                    session=session,
                    parent_collection_id=collection_id,
                    annotations=annotations,
                )

                results.append(
                    ProviderResult(
                        sample_id=sample.sample_id,
                        success=True,
                        data={"detections": detections},
                    )
                )
            except Exception as e:
                results.append(
                    ProviderResult(
                        sample_id=sample.sample_id,
                        success=False,
                        error_message=str(e),
                    )
                )

        return results

    def _detect_objects(
        self,
        api_url: str,
        sample: SampleTable,
        class_prompts: dict[str, str],
        threshold: float,
    ) -> list[dict]:
        """Call open vocabulary detection API.

        Args:
            api_url: URL of the inference server.
            sample: Sample to detect objects in.
            class_prompts: Dictionary mapping class names to prompts.
            threshold: Confidence threshold for detections.

        Returns:
            List of detection dictionaries with class_name, confidence, and bbox.
        """
        # Get image path from the database
        from lightly_studio.models.image import ImageTable
        from sqlalchemy.orm import Session

        session = Session.object_session(sample)
        if session is None:
            raise RuntimeError("No database session found for sample")

        image = session.get(ImageTable, sample.sample_id)
        if not image:
            raise ValueError(f"No image found for sample {sample.sample_id}")

        # Call the detection API
        response = self._make_api_request(
            url=api_url,
            method="POST",
            json_data={
                "image_path": image.file_path_abs,
                "classes": class_prompts,
                "confidence_threshold": threshold,
            },
        )

        # Return detections from response
        return response.get("detections", [])
