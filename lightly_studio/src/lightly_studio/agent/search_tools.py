"""Agent tools that read the collection and find samples by embedding similarity."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field

from lightly_studio.agent import sample_source
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database.db_vector import Embedding
from lightly_studio.embed import embed_samples
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

# The largest number of samples that one search returns.
MAX_SEARCH_LIMIT = 1000

# The number of samples that one database page of a search reads. `Paginated` allows 100.
_PAGE_SIZE = 100

# The number of best samples whose file names a search result shows to the model.
_PREVIEW_SIZE = 5


class SearchByTextArgs(BaseModel):
    """Arguments of ``search_by_text``."""

    query: str = Field(min_length=1, description="What the images show, e.g. 'a tiger'.")
    limit: int = Field(
        gt=0,
        le=MAX_SEARCH_LIMIT,
        description=(
            "How many of the best samples to return. The search ranks all samples and does "
            "not filter them, so it always returns this many. When the user gives no number, "
            "use 20. Never use the collection size."
        ),
    )
    within: str | None = Field(
        default=None,
        description="Optional. Search only these samples. " + sample_source.SOURCE_DESCRIPTION,
    )


class FindSimilarArgs(BaseModel):
    """Arguments of ``find_similar_samples``."""

    source: str = Field(description="The query samples. " + sample_source.SOURCE_DESCRIPTION)
    limit: int = Field(gt=0, le=MAX_SEARCH_LIMIT, description="How many samples to return.")


@dataclass(frozen=True)
class _RankedSample:
    sample_id: UUID
    file_name: str
    similarity: float


def search_by_text(context: AgentContext, args: SearchByTextArgs) -> dict[str, Any]:
    """Rank the samples by their similarity to a text query."""
    query_embedding = embed_samples.embed_text_for_collection(
        session=context.session, collection_id=context.collection.collection_id, text=args.query
    )
    within = None if args.within is None else sample_source.resolve_source(context, args.within)
    ranked = _rank_by_embedding(
        context=context,
        query_embedding=query_embedding,
        limit=args.limit,
        within=within,
        exclude=set(),
    )
    return _store_ranked(context=context, ranked=ranked)


def find_similar_samples(context: AgentContext, args: FindSimilarArgs) -> dict[str, Any]:
    """Rank the samples by their similarity to a set of query samples."""
    source_ids = sample_source.resolve_source(context, args.source)
    embeddings = _get_embeddings(context=context, sample_ids=source_ids)
    ranked = _rank_by_embedding(
        context=context,
        query_embedding=aggregate_query_embedding(embeddings=embeddings),
        limit=args.limit,
        within=None,
        # The query samples are trivially similar to themselves.
        exclude=set(source_ids),
    )
    return _store_ranked(context=context, ranked=ranked)


def aggregate_query_embedding(embeddings: Sequence[Embedding]) -> list[float]:
    """Combine the embeddings of several query samples into one query vector.

    The ranking uses cosine distance, so only the direction of the vector matters. Each
    embedding is scaled to unit length before the mean, so every query sample has the same
    weight. Zero vectors have no direction and are left out.

    Args:
        embeddings: The embeddings of the query samples. Not empty.

    Returns:
        The query vector.

    Raises:
        ValueError: If there are no embeddings, or if every embedding is a zero vector.
    """
    if not embeddings:
        raise ValueError("There are no embeddings of the query samples.")
    matrix = np.stack(embeddings).astype(np.float64)
    norms = np.linalg.norm(matrix, axis=1)
    nonzero = norms > 0
    if not nonzero.any():
        raise ValueError("The query samples have only zero embeddings.")
    unit_vectors = matrix[nonzero] / norms[nonzero, np.newaxis]
    query: list[float] = unit_vectors.mean(axis=0).tolist()
    return query


SEARCH_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="search_by_text",
        description=(
            "Find the samples whose image content best matches a text query, with the "
            "embedding model of the collection. The result is a ranking by similarity, not a "
            "filter. Returns a result handle, the count and the best matches. Use it for "
            "requests such as 'images of a tiger'."
        ),
        args_model=SearchByTextArgs,
        run=search_by_text,
    ),
    AgentTool(
        name="find_similar_samples",
        description=(
            "Find the samples that look most similar to a set of query samples. The query "
            "samples themselves are left out. Returns a result handle, the count and the "
            "best matches."
        ),
        args_model=FindSimilarArgs,
        run=find_similar_samples,
    ),
]


def _rank_by_embedding(
    context: AgentContext,
    query_embedding: list[float],
    limit: int,
    within: list[UUID] | None,
    exclude: set[UUID],
) -> list[_RankedSample]:
    """Read the samples in order of similarity, one page at a time, until ``limit``."""
    filters = None if within is None else ImageFilter(sample_filter=SampleFilter(sample_ids=within))
    ranked: list[_RankedSample] = []
    offset: int | None = 0
    while offset is not None and len(ranked) < limit:
        page = image_resolver.get_all_by_collection_id(
            session=context.session,
            collection_id=context.collection.collection_id,
            pagination=Paginated(offset=offset, limit=_PAGE_SIZE),
            filters=filters,
            text_embedding=query_embedding,
        )
        scores = page.similarity_scores or []
        ranked.extend(
            _RankedSample(sample_id=image.sample_id, file_name=image.file_name, similarity=score)
            for image, score in zip(page.samples, scores)
            if image.sample_id not in exclude
        )
        offset = page.next_cursor
    return ranked[:limit]


def _get_embeddings(context: AgentContext, sample_ids: list[UUID]) -> list[Embedding]:
    embedding_model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=context.session, collection_id=context.collection.collection_id
    )
    if embedding_model_id is None:
        raise ValueError("The collection has no embeddings.")
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=context.session, sample_ids=sample_ids, embedding_model_id=embedding_model_id
    )
    if not rows:
        raise ValueError("The query samples have no embeddings.")
    return [row.embedding for row in rows]


def _store_ranked(context: AgentContext, ranked: list[_RankedSample]) -> dict[str, Any]:
    """Store the ranked samples behind a handle and summarize them for the model."""
    handle = context.result_store.put(
        collection_id=context.collection.collection_id,
        sample_ids=[sample.sample_id for sample in ranked],
    )
    return {
        "result": handle,
        "count": len(ranked),
        "best_matches": [
            {"file_name": sample.file_name, "similarity": round(sample.similarity, 3)}
            for sample in ranked[:_PREVIEW_SIZE]
        ],
    }
