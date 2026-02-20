"""Implementation of get_all_by_collection_id function for images."""

from __future__ import annotations

from collections.abc import Sequence
import logging
import time
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import ColumnElement
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)

logger = logging.getLogger(__name__)


class GetAllSamplesByCollectionIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[ImageTable]
    total_count: int
    next_cursor: int | None = None
    similarity_scores: Sequence[float] | None = None


def _get_load_options() -> LoaderOption:
    """Get common load options for the sample relationship."""
    return selectinload(ImageTable.sample).options(
        joinedload(SampleTable.tags),
        # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
        joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
        selectinload(SampleTable.captions),
        selectinload(SampleTable.annotations).options(
            joinedload(AnnotationBaseTable.annotation_label),
            joinedload(AnnotationBaseTable.object_detection_details),
            joinedload(AnnotationBaseTable.segmentation_details),
        ),
    )


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute next cursor for pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None


def get_all_by_collection_id(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
) -> GetAllSamplesByCollectionIdResult:
    """Retrieve samples for a specific collection with optional filtering."""
    t0 = time.perf_counter()
    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )
    t1 = time.perf_counter()
    logger.info(
        "image_resolver get_all_by_collection_id: distance_expr=%.3fs similarity=%s",
        t1 - t0,
        distance_expr is not None and embedding_model_id is not None,
    )

    if distance_expr is not None and embedding_model_id is not None:
        result = _get_all_with_similarity(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            distance_expr=distance_expr,
            pagination=pagination,
            filters=filters,
            sample_ids=sample_ids,
        )
    else:
        result = _get_all_without_similarity(
            session=session,
            collection_id=collection_id,
            pagination=pagination,
            filters=filters,
            sample_ids=sample_ids,
        )
    t2 = time.perf_counter()
    logger.info("image_resolver get_all_by_collection_id total=%.3fs", t2 - t0)
    return result


def _get_all_with_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    distance_expr: ColumnElement[float],
    pagination: Paginated | None,
    filters: ImageFilter | None,
    sample_ids: list[UUID] | None,
) -> GetAllSamplesByCollectionIdResult:
    """Get samples with similarity search - returns (ImageTable, float) tuples."""
    t0 = time.perf_counter()
    load_options = _get_load_options()

    samples_query = (
        select(ImageTable, distance_expr)
        .options(load_options)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    samples_query = apply_similarity_join(
        query=samples_query,
        sample_id_column=col(ImageTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    total_count_query = apply_similarity_join(
        query=total_count_query,
        sample_id_column=col(ImageTable.sample_id),
        embedding_model_id=embedding_model_id,
    )
    t1 = time.perf_counter()

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(ImageTable.sample_id).in_(sample_ids))

    samples_query = samples_query.order_by(distance_expr)

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    t2 = time.perf_counter()
    total_count = session.exec(total_count_query).one()
    t3 = time.perf_counter()
    results = session.exec(samples_query).all()
    t4 = time.perf_counter()

    samples = [r[0] for r in results]
    similarity_scores = [distance_to_similarity(r[1]) for r in results]
    t5 = time.perf_counter()

    logger.info(
        "image_resolver similarity timings: build=%.3fs apply=%.3fs count=%.3fs samples=%.3fs post=%.3fs total=%.3fs",
        t1 - t0,
        t2 - t1,
        t3 - t2,
        t4 - t3,
        t5 - t4,
        t5 - t0,
    )

    return GetAllSamplesByCollectionIdResult(
        samples=samples,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
        similarity_scores=similarity_scores,
    )


def _get_all_without_similarity(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
    filters: ImageFilter | None,
    sample_ids: list[UUID] | None,
) -> GetAllSamplesByCollectionIdResult:
    """Get samples without similarity search - returns ImageTable directly."""
    t0 = time.perf_counter()
    load_options = _get_load_options()

    samples_query = (
        select(ImageTable)
        .options(load_options)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    t1 = time.perf_counter()

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(ImageTable.sample_id).in_(sample_ids))

    samples_query = samples_query.order_by(col(ImageTable.file_path_abs).asc())

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    t2 = time.perf_counter()
    total_count = session.exec(total_count_query).one()
    t3 = time.perf_counter()
    samples = session.exec(samples_query).all()
    t4 = time.perf_counter()

    logger.info(
        "image_resolver timings: build=%.3fs apply=%.3fs count=%.3fs samples=%.3fs total=%.3fs",
        t1 - t0,
        t2 - t1,
        t3 - t2,
        t4 - t3,
        t4 - t0,
    )

    return GetAllSamplesByCollectionIdResult(
        samples=samples,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
        similarity_scores=None,
    )
