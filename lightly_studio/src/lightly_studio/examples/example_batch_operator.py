"""Example of how to register a custom BatchSampleOperator (e.g., auto-labeling)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
import lightly_studio.plugins  # noqa: F401
from lightly_studio import db_manager
from lightly_studio.plugins.base_operator import BatchSampleOperator, SampleResult
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.parameter import (
    BaseParameter,
    FloatParameter,
    StringParameter,
    TagFilterParameter,
)


class MockDetectorOperator(BatchSampleOperator):
    """Example batch operator that simulates running a detector on each sample."""

    @property
    def name(self) -> str:
        return "Mock Object Detector"

    @property
    def description(self) -> str:
        return "Simulates object detection — returns dummy bounding boxes per sample"

    @property
    def parameters(self) -> list[BaseParameter]:
        return [
            StringParameter(
                name="api_url",
                description="URL of the detection server",
                default="http://localhost:8001/detect",
            ),
            FloatParameter(
                name="confidence_threshold",
                description="Minimum detection confidence",
                default=0.5,
                required=False,
            ),
            TagFilterParameter(
                name="tag_filter",
                description="Only process samples with this tag",
                required=False,
            ),
            StringParameter(
                name="result_tag_name",
                description="Tag name applied to processed samples",
                default="mock-detected",
            ),
        ]

    def execute_batch(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> list[SampleResult]:
        threshold = parameters.get("confidence_threshold", 0.5)

        # Get samples (respects tag_filter if provided)
        samples = self._get_samples_by_filter(session, collection_id)

        results = []
        for sample in samples:
            # In a real operator you would call an external API here, e.g.:
            #   response = self._make_api_request(url=api_url, json_data={...})
            results.append(
                SampleResult(
                    sample_id=sample.sample_id,
                    success=True,
                    data={
                        "detections": [
                            {"class": "car", "confidence": 0.9, "bbox": [0.1, 0.2, 0.3, 0.4]},
                        ]
                    },
                )
            )

        return results


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Register the custom operator with a deterministic ID
operator_registry.register(
    MockDetectorOperator(), operator_id="mock_detector"
)

# Define data path
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create dataset and load images
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path)

ls.start_gui()
