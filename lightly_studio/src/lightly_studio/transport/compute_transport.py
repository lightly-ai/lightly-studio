"""Transport protocol for computations on samples."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeAlias
from uuid import UUID

from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    InstanceSegmentationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.sampling.sampling_config import SamplingConfig

EvaluationConfig: TypeAlias = (
    ClassificationEvaluationConfig
    | InstanceSegmentationEvaluationConfig
    | ObjectDetectionEvaluationConfig
    | SemanticSegmentationEvaluationConfig
)


class ComputeTransport(Protocol):
    """Runs metadata computations, selection and evaluation."""

    def compute_typicality(
        self, collection_id: UUID, embedding_model_name: str | None, metadata_name: str
    ) -> None:
        """Compute the typicality of each sample and store it as metadata.

        Args:
            collection_id: The ID of the collection.
            embedding_model_name: The embedding model. None uses the default model.
            metadata_name: The metadata key for the values.
        """

    def compute_similarity(
        self,
        collection_id: UUID,
        query_tag_name: str,
        embedding_model_name: str | None,
        metadata_name: str | None,
    ) -> str:
        """Compute the similarity of each sample to the tagged samples and store it as metadata.

        Args:
            collection_id: The ID of the collection.
            query_tag_name: The tag of the query samples.
            embedding_model_name: The embedding model. None uses the default model.
            metadata_name: The metadata key for the values. None makes a new key.

        Returns:
            The metadata key for the values.
        """

    def select(self, config: SamplingConfig, sample_ids: Sequence[UUID]) -> None:
        """Select samples from `sample_ids` and tag them with the tag of `config`."""

    def evaluate(
        self,
        sample_ids: Sequence[UUID],
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: EvaluationConfig,
    ) -> EvaluationResult:
        """Evaluate predictions against ground truth and store the metrics.

        Args:
            sample_ids: The samples to evaluate.
            name: The name of the evaluation run.
            gt_annotation_source: The annotation source with the ground truth.
            pred_annotation_source: The annotation source with the predictions.
            config: The evaluation config. Its type sets the evaluation task.
        """
