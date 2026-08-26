"""Shared database helpers for sampling."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.database.db_vector import Embedding
from lightly_studio.resolvers import (
    embedding_model_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


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


def get_embeddings_by_tag_id(
    session: Session,
    collection_id: UUID,
    tag_id: UUID,
    embedding_model_name: str | None,
) -> list[Embedding]:
    """Resolve sample embeddings for the given model and sample tag."""
    embedding_model_id = embedding_model_resolver.get_by_name(
        session=session,
        collection_id=collection_id,
        embedding_model_name=embedding_model_name,
    ).embedding_model_id
    embedding_tables = sample_embedding_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        filters=SampleFilter(tag_ids=[tag_id]),
    )
    return [embedding.embedding for embedding in embedding_tables]


def create_result_tag(
    session: Session,
    collection_id: UUID,
    tag_name: str,
    selected_sample_ids: Sequence[UUID],
) -> None:
    """Attach the selected sample ids to the result sample tag, creating it if needed.

    An existing tag is extended rather than replaced, which is how a run that reuses
    its preselected tag name grows that tag. Callers must have rejected any other
    name collision beforehand.
    """
    tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=session,
        collection_id=collection_id,
        tag_name=tag_name,
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=tag.tag_id, sample_ids=list(selected_sample_ids)
    )
