"""Transport protocol for computations on samples."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.sampling.sampling_config import SamplingConfig


# TODO(Iunir, 11/2026): Add evaluation when its config and result models have no DB imports.
class ComputeTransport(Protocol):
    """Runs metadata computations and selection.

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

    def select(self, config: SamplingConfig, query_expr: QueryExpr | None) -> None:
        """Select samples and tag them with the tag of `config`.

        Args:
            config: The sampling config. It also sets the collection.
            query_expr: The samples to select from. None uses all samples of the collection.
        """
