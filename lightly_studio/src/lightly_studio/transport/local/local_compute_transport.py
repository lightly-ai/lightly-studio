"""Compute transport that calls the services in the same process."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.evaluation.image_dataset_evaluate import ImageDatasetEvaluate
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_metrics import EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationRunView
from lightly_studio.models.evaluation_task import EvaluationResult, EvaluationTask
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.resolvers import collection_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.sampling import sampling_via_db
from lightly_studio.sampling.sampling_config import SamplingConfig
from lightly_studio.services import compute_metadata_service, evaluation_service
from lightly_studio.services.sample_services import sample_query_service


class LocalComputeTransport:
    """Implements `ComputeTransport` with the persistent database session."""

    def compute_typicality(
        self, collection_id: UUID, embedding_model_name: str | None, metadata_name: str
    ) -> None:
        """Compute the typicality of each sample and store it as metadata."""
        compute_metadata_service.compute_typicality_metadata(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            embedding_model_name=embedding_model_name,
            metadata_name=metadata_name,
        )

    def compute_similarity(
        self,
        collection_id: UUID,
        query_tag_name: str,
        embedding_model_name: str | None,
        metadata_name: str | None,
    ) -> str:
        """Compute the similarity of each sample to the tagged samples and store it as metadata."""
        session = db_manager.persistent_session()
        query_tag = tag_resolver.get_by_name(
            session=session, tag_name=query_tag_name, collection_id=collection_id
        )
        if query_tag is None:
            raise ValueError("Query tag not found")
        return compute_metadata_service.compute_similarity_metadata(
            session=session,
            collection_id=collection_id,
            query_tag_id=query_tag.tag_id,
            embedding_model_name=embedding_model_name,
            metadata_name=metadata_name,
        )

    def sampling(
        self, config: SamplingConfig, request: SampleQueryRequest, limit: int | None
    ) -> None:
        """Sample from the matching image samples and tag the result with the tag of `config`.

        Raises:
            ValueError: If the collection is not an image collection.
        """
        session = db_manager.persistent_session()
        collection = collection_resolver.get_by_id(
            session=session, collection_id=config.collection_id
        )
        if collection is None or collection.sample_type != SampleType.IMAGE:
            raise ValueError(f"Collection {config.collection_id} is not an image collection.")
        input_sample_ids = sample_query_service.get_sample_ids(
            session=session, collection_id=config.collection_id, request=request, limit=limit
        )
        sampling_via_db.sampling_via_database(
            session=session, config=config, input_sample_ids=input_sample_ids
        )

    def evaluate(
        self, collection_id: UUID, query_expr: QueryExpr | None, task: EvaluationTask
    ) -> EvaluationResult:
        """Create an evaluation run on the matching image samples and store its metrics."""
        session = db_manager.persistent_session()
        collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if collection is None:
            raise ValueError(f"Collection {collection_id} not found.")
        return evaluation_service.run_evaluation(
            session=session,
            collection=collection,
            task_type=task.task_type,
            gt_annotation_source=task.gt_annotation_source,
            pred_annotation_source=task.pred_annotation_source,
            config=task.config,
            filters=ImageFilter(sample_filter=SampleFilter(query_expr=query_expr)),
            name=task.name,
        )

    def list_evaluation_runs(self, collection_id: UUID) -> list[EvaluationRunView]:
        """List the evaluation runs of the dataset of a collection, newest first."""
        return _evaluation_of_dataset(collection_id=collection_id).list_runs()

    def get_evaluation_confusion_matrix(self, collection_id: UUID, run_id: UUID) -> ConfusionMatrix:
        """Get the confusion matrix of an evaluation run of the dataset of a collection."""
        return _evaluation_of_dataset(collection_id=collection_id).confusion_matrix(run_id=run_id)

    def get_evaluation_metrics(self, collection_id: UUID, run_id: UUID) -> EvaluationMetrics:
        """Get the aggregate metrics of an evaluation run of the dataset of a collection."""
        return _evaluation_of_dataset(collection_id=collection_id).metrics(run_id=run_id)


def _evaluation_of_dataset(collection_id: UUID) -> ImageDatasetEvaluate:
    """Get the evaluation of the dataset of a collection, without samples to evaluate."""
    return ImageDatasetEvaluate(
        session=db_manager.persistent_session(), collection_id=collection_id, sample_ids=()
    )
