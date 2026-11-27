"""Compute transport that calls the services in the same process."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.resolvers import collection_resolver, image_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.sampling import sampling_via_db
from lightly_studio.sampling.sampling_config import SamplingConfig
from lightly_studio.services import compute_metadata_service


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

    def sampling(self, config: SamplingConfig, query_expr: QueryExpr | None) -> None:
        """Sample from the matching image samples and tag the result with the tag of `config`.

        The candidates have the default order of a dataset query, because the order changes
        the selection.

        Raises:
            ValueError: If the collection is not an image collection.
        """
        session = db_manager.persistent_session()
        collection = collection_resolver.get_by_id(
            session=session, collection_id=config.collection_id
        )
        if collection is None or collection.sample_type != SampleType.IMAGE:
            raise ValueError(f"Collection {config.collection_id} is not an image collection.")
        input_sample_ids = image_resolver.get_ordered_sample_ids(
            session=session,
            collection_id=config.collection_id,
            filters=ImageFilter(sample_filter=SampleFilter(query_expr=query_expr)),
        )
        sampling_via_db.sampling_via_database(
            session=session, config=config, input_sample_ids=input_sample_ids
        )
