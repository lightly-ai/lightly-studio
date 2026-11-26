"""Compute transport that calls the services in the same process."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.resolvers import tag_resolver
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
        """Sample from the matching samples. The local compute transport cannot sample yet."""
        raise NotImplementedError("The local compute transport cannot sample yet.")
