"""Compute metadata as part of a sampling request."""

from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.metadata import compute_similarity, compute_typicality
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import collection_embedding_model_resolver, tag_resolver


class TypicalityComputation(BaseModel):
    """Typicality metadata required before selection."""

    kind: Literal["typicality"]
    metadata_name: str = Field(min_length=1)


class SimilarityComputation(BaseModel):
    """Similarity metadata required before selection."""

    kind: Literal["similarity"]
    metadata_name: str = Field(min_length=1)
    query_tag_id: UUID


MetadataComputation = Annotated[
    Union[TypicalityComputation, SimilarityComputation], Field(discriminator="kind")
]


def compute_metadata(
    session: Session,
    collection: CollectionTable,
    computations: list[MetadataComputation],
) -> None:
    """Prepare metadata atomically using the collection's default embedding model.

    Roll back all metadata updates in the batch if any computation fails.
    Selection runs after this transaction and is not part of the rollback.
    """
    if not computations:
        return
    try:
        # Resolvers commit individually. Joining the outer transaction prevents those commits
        # from persisting a partial batch, without requiring savepoints unsupported by DuckDB.
        with Session(
            bind=session.connection(), join_transaction_mode="rollback_only"
        ) as batch_session:
            _compute_metadata(
                session=batch_session, collection=collection, computations=computations
            )
        session.commit()
    except Exception:
        session.rollback()
        raise


def _compute_metadata(
    session: Session,
    collection: CollectionTable,
    computations: list[MetadataComputation],
) -> None:
    """Compute the batch without committing individual metadata updates."""
    for computation in computations:
        if isinstance(computation, SimilarityComputation):
            if collection.sample_type != SampleType.IMAGE:
                raise ValueError("Similarity is only available for image collections.")
            tag = tag_resolver.get_by_id(session=session, tag_id=computation.query_tag_id)
            if tag is None or tag.collection_id != collection.collection_id:
                raise ValueError("Similarity query tag must belong to the sampling collection.")

        embedding_model_id = collection_embedding_model_resolver.get_model_id_by_name(
            session=session,
            collection_id=collection.collection_id,
            embedding_model_name=None,
        )
        if isinstance(computation, TypicalityComputation):
            compute_typicality.compute_typicality_metadata(
                session=session,
                collection_id=collection.collection_id,
                embedding_model_id=embedding_model_id,
                metadata_name=computation.metadata_name,
            )
        else:
            compute_similarity.compute_similarity_metadata(
                session=session,
                key_collection_id=collection.collection_id,
                embedding_model_id=embedding_model_id,
                query_tag_id=computation.query_tag_id,
                metadata_name=computation.metadata_name,
            )
