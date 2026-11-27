"""Transport protocol for computations on samples."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_metrics import EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationRunView
from lightly_studio.models.evaluation_task import EvaluationResult, EvaluationTask
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.sampling.sampling_config import SamplingConfig


class ComputeTransport(Protocol):
    """Runs metadata computations, sampling and evaluation.

    The server finds the matching samples, so a remote call sends no list of sample IDs.
    """

    def compute_typicality(
        self, collection_id: UUID, embedding_model_name: str | None, metadata_name: str
    ) -> None:
        """Compute the typicality of each sample and store it as metadata.

        Args:
            collection_id: The ID of the collection.
            embedding_model_name: The embedding model. None uses the default model.
            metadata_name: The metadata key for the values.

        Raises:
            ValueError: If the embedding model does not exist.
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

        Raises:
            ValueError: If the query tag or the embedding model does not exist.
        """

    def sampling(
        self, config: SamplingConfig, request: SampleQueryRequest, limit: int | None
    ) -> None:
        """Sample from the matching samples and tag the result with the tag of `config`.

        Only image collections are supported.

        Args:
            config: The sampling config. It also sets the collection.
            request: The filter, the sort and the offset of the samples to sample from. The
                `cursor` and the `limit` of the request are not used.
            limit: The maximum number of samples to sample from. None uses all.
        """

    def evaluate(
        self,
        collection_id: UUID,
        request: SampleQueryRequest,
        limit: int | None,
        task: EvaluationTask,
    ) -> EvaluationResult:
        """Create an evaluation run on the matching samples and store its metrics.

        Args:
            collection_id: The ID of the collection.
            request: The filter, the sort and the offset of the samples to evaluate. The
                `cursor` and the `limit` of the request are not used.
            limit: The maximum number of samples to evaluate. None uses all.
            task: The evaluation run to create.

        Returns:
            The number of samples and annotations that the run uses.

        Raises:
            ValueError: If the collection does not exist or is not an image collection, or an
                annotation source is not valid for the task.
        """

    def list_evaluation_runs(self, collection_id: UUID) -> list[EvaluationRunView]:
        """List the evaluation runs of the dataset of a collection, newest first.

        Raises:
            ValueError: If the collection does not exist.
        """

    def get_evaluation_confusion_matrix(self, collection_id: UUID, run_id: UUID) -> ConfusionMatrix:
        """Get the confusion matrix of an evaluation run of the dataset of a collection.

        Raises:
            ValueError: If the collection does not exist, or the run does not exist in its dataset.
            NotImplementedError: If the task type of the run has no confusion matrix.
        """

    def get_evaluation_metrics(self, collection_id: UUID, run_id: UUID) -> EvaluationMetrics:
        """Get the aggregate metrics of an evaluation run of the dataset of a collection.

        Raises:
            ValueError: If the collection does not exist, or the run does not exist in its dataset.
            NotImplementedError: If the task type of the run has no confusion matrix.
        """
