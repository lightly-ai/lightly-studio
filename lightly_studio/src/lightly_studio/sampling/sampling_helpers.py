"""Shared database helpers for sampling."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    embedding_model_resolver,
    sample_embedding_resolver,
    tag_resolver,
)


def get_embeddings_by_sample_ids(
    session: Session,
    collection_id: UUID,
    sample_ids: Sequence[UUID],
    embedding_model_name: str | None,
) -> list[Embedding]:
    """Resolve sample embeddings for the given model and sample ids.

    Output order matches ``sample_ids``.
    """
    embedding_model_id = embedding_model_resolver.get_by_name(
        session=session,
        collection_id=collection_id,
        embedding_model_name=embedding_model_name,
    ).embedding_model_id
    embedding_tables = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=list(sample_ids),
        embedding_model_id=embedding_model_id,
    )
    return [embedding.embedding for embedding in embedding_tables]


def create_result_tag(
    session: Session,
    collection_id: UUID,
    tag_name: str,
    selected_sample_ids: Sequence[UUID],
) -> None:
    """Create a sample tag and attach the selected sample ids."""
    tag = tag_resolver.create(
        session=session,
        tag=TagCreate(
            collection_id=collection_id,
            name=tag_name,
            kind="sample",
        ),
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=tag.tag_id, sample_ids=list(selected_sample_ids)
    )
