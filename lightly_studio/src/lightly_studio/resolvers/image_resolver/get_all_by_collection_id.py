"""Implementation of get_all_by_collection_id function for images."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.similarity_utils import (
    distance_to_similarity,
    get_distance_expression,
)


class GetAllSamplesByCollectionIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[ImageTable]
    total_count: int
    next_cursor: int | None = None
    similarity_scores: Sequence[float] | None = None


def _get_load_options() -> Any:
    """Get common load options for the sample relationship."""
    return selectinload(ImageTable.sample).options(
        joinedload(SampleTable.tags),
        # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
        joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
        selectinload(SampleTable.captions),
        selectinload(SampleTable.annotations).options(
            joinedload(AnnotationBaseTable.annotation_label),
            joinedload(AnnotationBaseTable.object_detection_details),
            joinedload(AnnotationBaseTable.instance_segmentation_details),
            joinedload(AnnotationBaseTable.semantic_segmentation_details),
            selectinload(AnnotationBaseTable.tags),
        ),
    )


def get_all_by_collection_id(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
) -> GetAllSamplesByCollectionIdResult:
    """Retrieve samples for a specific collection with optional filtering."""
    load_options = _get_load_options()
    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    # Build the samples query. Use select(ImageTable, distance_expr) when doing
    # similarity search so that session.exec() returns tuples instead of scalars.
    if distance_expr is not None:
        samples_query = (
            select(ImageTable, distance_expr)
            .options(load_options)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .join(
                SampleEmbeddingTable,
                col(ImageTable.sample_id) == col(SampleEmbeddingTable.sample_id),
            )
            .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        )
    else:
        samples_query = (
            select(ImageTable)  # type: ignore[assignment]
            .options(load_options)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
        )

    # Build total count query.
    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    if distance_expr is not None:
        total_count_query = total_count_query.join(
            SampleEmbeddingTable,
            col(ImageTable.sample_id) == col(SampleEmbeddingTable.sample_id),
        ).where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)

    # Apply filters.
    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(ImageTable.sample_id).in_(sample_ids))

    # Apply ordering.
    if distance_expr is not None:
        samples_query = samples_query.order_by(distance_expr)
    else:
        samples_query = samples_query.order_by(col(ImageTable.file_path_abs).asc())

    # Apply pagination.
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()

    # Process results.
    similarity_scores = None
    samples: Sequence[ImageTable]
    if distance_expr is not None:
        # Results are tuples of (ImageTable, distance).
        samples = [r[0] for r in results]
        similarity_scores = [distance_to_similarity(r[1]) for r in results]
    else:
        samples = results  # type: ignore[assignment]

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return GetAllSamplesByCollectionIdResult(
        samples=samples,
        total_count=total_count,
        next_cursor=next_cursor,
        similarity_scores=similarity_scores,
    )
