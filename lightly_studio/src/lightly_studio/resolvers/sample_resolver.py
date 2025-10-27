"""Handler for database operations related to samples."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.samples_filter import SampleFilter


def create(session: Session, sample: ImageCreate) -> ImageTable:
    """Create a new sample in the database."""
    db_sample = ImageTable.model_validate(sample)
    session.add(db_sample)
    session.commit()
    session.refresh(db_sample)
    return db_sample


def create_many(session: Session, samples: list[ImageCreate]) -> list[ImageTable]:
    """Create multiple samples in a single database commit."""
    db_samples = [ImageTable.model_validate(sample) for sample in samples]
    session.bulk_save_objects(db_samples)
    session.commit()
    return db_samples


def filter_new_paths(session: Session, file_paths_abs: list[str]) -> tuple[list[str], list[str]]:
    """Return a) file_path_abs that do not already exist in the database and b) those that do."""
    existing_file_paths_abs = set(
        session.exec(
            select(col(ImageTable.file_path_abs)).where(
                col(ImageTable.file_path_abs).in_(file_paths_abs)
            )
        ).all()
    )
    file_paths_abs_set = set(file_paths_abs)
    return (
        list(file_paths_abs_set - existing_file_paths_abs),  # paths that are not in the DB
        list(file_paths_abs_set & existing_file_paths_abs),  # paths that are already in the DB
    )


def get_by_id(session: Session, dataset_id: UUID, sample_id: UUID) -> ImageTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(
        select(ImageTable).where(
            ImageTable.sample_id == sample_id, ImageTable.dataset_id == dataset_id
        )
    ).one_or_none()


def count_by_dataset_id(session: Session, dataset_id: UUID) -> int:
    """Count the number of samples in a dataset."""
    return session.exec(
        select(func.count()).select_from(ImageTable).where(ImageTable.dataset_id == dataset_id)
    ).one()


def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[ImageTable]:
    """Retrieve multiple samples by their IDs.

    Output order matches the input order.
    """
    results = session.exec(
        select(ImageTable).where(col(ImageTable.sample_id).in_(sample_ids))
    ).all()
    # Return samples in the same order as the input IDs
    sample_map = {sample.sample_id: sample for sample in results}
    return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]


class GetAllSamplesByDatasetIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[ImageTable]
    total_count: int
    next_cursor: int | None = None


def get_all_by_dataset_id(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    pagination: Paginated | None = None,
    filters: SampleFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
) -> GetAllSamplesByDatasetIdResult:
    """Retrieve samples for a specific dataset with optional filtering."""
    samples_query = (
        select(ImageTable)
        .options(
            selectinload(ImageTable.annotations).options(
                joinedload(AnnotationBaseTable.annotation_label),
                joinedload(AnnotationBaseTable.object_detection_details),
                joinedload(AnnotationBaseTable.instance_segmentation_details),
                joinedload(AnnotationBaseTable.semantic_segmentation_details),
            ),
            selectinload(ImageTable.captions),
            selectinload(ImageTable.tags),
            # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
            joinedload(ImageTable.metadata_dict),  # type: ignore[arg-type]
        )
        .where(ImageTable.dataset_id == dataset_id)
    )
    total_count_query = (
        select(func.count()).select_from(ImageTable).where(ImageTable.dataset_id == dataset_id)
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
            .where(EmbeddingModelTable.dataset_id == dataset_id)
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


def get_dimension_bounds(
    session: Session,
    dataset_id: UUID,
    annotation_label_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
) -> dict[str, int]:
    """Get min and max dimensions of samples in a dataset."""
    # Prepare the base query for dimensions
    query: Select[tuple[int | None, int | None, int | None, int | None]] = select(
        func.min(ImageTable.width).label("min_width"),
        func.max(ImageTable.width).label("max_width"),
        func.min(ImageTable.height).label("min_height"),
        func.max(ImageTable.height).label("max_height"),
    )

    if annotation_label_ids:
        # Subquery to filter samples matching all annotation labels
        label_filter = (
            select(ImageTable.sample_id)
            .join(
                AnnotationBaseTable,
                col(ImageTable.sample_id) == col(AnnotationBaseTable.sample_id),
            )
            .join(
                AnnotationLabelTable,
                col(AnnotationBaseTable.annotation_label_id)
                == col(AnnotationLabelTable.annotation_label_id),
            )
            .where(
                ImageTable.dataset_id == dataset_id,
                col(AnnotationLabelTable.annotation_label_id).in_(annotation_label_ids),
            )
            .group_by(col(ImageTable.sample_id))
            .having(
                func.count(col(AnnotationLabelTable.annotation_label_id).distinct())
                == len(annotation_label_ids)
            )
        )
        # Filter the dimension query based on the subquery
        query = query.where(col(ImageTable.sample_id).in_(label_filter))
    else:
        # If no labels specified, filter dimensions
        # for all samples in the dataset
        query = query.where(ImageTable.dataset_id == dataset_id)

    if tag_ids:
        query = (
            query.join(ImageTable.tags)
            .where(ImageTable.tags.any(col(TagTable.tag_id).in_(tag_ids)))
            .distinct()
        )

    # Note: We use SQLAlchemy's session.execute instead of SQLModel's
    # ession.exec to be able to fetch the columns with names with the
    # `mappings()` method.
    result = session.execute(query).mappings().one()
    return {key: value for key, value in result.items() if value is not None}


def update(session: Session, sample_id: UUID, sample_data: ImageCreate) -> ImageTable | None:
    """Update an existing sample."""
    sample = get_by_id(session=session, dataset_id=sample_data.dataset_id, sample_id=sample_id)
    if not sample:
        return None

    sample.file_name = sample_data.file_name
    sample.width = sample_data.width
    sample.height = sample_data.height
    sample.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(sample)
    return sample


def delete(session: Session, dataset_id: UUID, sample_id: UUID) -> bool:
    """Delete a sample."""
    sample = get_by_id(session=session, dataset_id=dataset_id, sample_id=sample_id)
    if not sample:
        return False

    session.delete(sample)
    session.commit()
    return True


def get_samples_excluding(
    session: Session,
    dataset_id: UUID,
    excluded_sample_ids: list[UUID],
    limit: int | None = None,
) -> Sequence[ImageTable]:
    """Get random samples excluding specified sample IDs.

    Args:
        session: The database session.
        dataset_id: The dataset ID to filter by.
        excluded_sample_ids: List of sample IDs to exclude from the result.
        limit: Maximum number of samples to return.
                If None, returns all matches.

    Returns:
        List of samples not associated with the excluded IDs.
    """
    query = (
        select(ImageTable)
        .where(ImageTable.dataset_id == dataset_id)
        .where(col(ImageTable.sample_id).not_in(excluded_sample_ids))
        .order_by(func.random())
    )

    if limit is not None:
        query = query.limit(limit)

    return session.exec(query).all()
