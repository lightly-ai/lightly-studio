"""Implementation of get_all_by_dataset_id function for images."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers.image_filter import ImageFilter


class GetAllSamplesByDatasetIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[ImageTable]
    total_count: int
    next_cursor: int | None = None


def get_all_by_dataset_id(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
) -> GetAllSamplesByDatasetIdResult:
    """Retrieve samples for a specific dataset with optional filtering."""
    samples_query = (
        select(ImageTable)
        .options(
            selectinload(ImageTable.sample).options(
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
            ),
        )
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == dataset_id)
    )
    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == dataset_id)
    )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(ImageTable.sample_id).in_(sample_ids))

    if text_embedding:
        # Fetch the first embedding_model_id for the given dataset_id
        embedding_model_id = session.exec(
            select(EmbeddingModelTable.embedding_model_id)
            .where(EmbeddingModelTable.collection_id == dataset_id)
            .limit(1)
        ).first()
        if embedding_model_id:
            # Join with SampleEmbedding table to access embeddings
            samples_query = (
                samples_query.join(
                    SampleEmbeddingTable,
                    col(ImageTable.sample_id) == col(SampleEmbeddingTable.sample_id),
                )
                .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
                .order_by(
                    func.list_cosine_distance(
                        SampleEmbeddingTable.embedding,
                        text_embedding,
                    )
                )
            )
            total_count_query = total_count_query.join(
                SampleEmbeddingTable,
                col(ImageTable.sample_id) == col(SampleEmbeddingTable.sample_id),
            ).where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
    else:
        samples_query = samples_query.order_by(col(ImageTable.file_path_abs).asc())

    # Apply pagination if provided
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return GetAllSamplesByDatasetIdResult(
        samples=session.exec(samples_query).all(),
        total_count=total_count,
        next_cursor=next_cursor,
    )
