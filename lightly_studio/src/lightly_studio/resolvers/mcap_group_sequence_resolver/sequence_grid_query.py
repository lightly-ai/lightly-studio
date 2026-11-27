"""Scope and order of the MCAP sequences grid query."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlmodel import col

from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import similarity_utils
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.type_definitions import QueryType


def scope_query(
    query: QueryType,
    collection_id: UUID,
    embedding_model_id: UUID | None,
    filters: McapSequenceFilter | None,
) -> QueryType:
    """Scope a query on McapGroupSequenceTable to a collection, embeddings and filters.

    With an embedding model, only sequences with an embedding of that model are kept.
    The grid and the previous/next navigation both use this scope, so they show the same
    sequences.
    """
    query = query.join(
        SampleTable, col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id)
    ).where(col(SampleTable.collection_id) == collection_id)
    query = similarity_utils.apply_similarity_join(
        query=query,
        sample_id_column=col(McapGroupSequenceTable.sample_id),
        embedding_model_id=embedding_model_id,
    )
    if filters is not None:
        query = filters.apply(query)
    return query


def default_order() -> list[ColumnElement[Any]]:
    """Order by creation time, with the sample ID as tiebreaker for a stable order."""
    return [col(SampleTable.created_at).asc(), col(SampleTable.sample_id).asc()]
