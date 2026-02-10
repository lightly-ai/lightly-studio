"""Implementation of get_all_by_collection_id function for groups."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.group import GroupTable, GroupView, GroupViewsWithCount
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)


def _get_load_options() -> LoaderOption:
    """Get common load options for the sample relationship."""
    return selectinload(GroupTable.sample).options(
        joinedload(SampleTable.tags),
        # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
        joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
        selectinload(SampleTable.captions),
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
    filters: GroupFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
) -> GroupViewsWithCount:
    """Retrieve groups for a specific collection with optional filtering."""
    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
        return _get_all_with_similarity(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            distance_expr=distance_expr,
            pagination=pagination,
            filters=filters,
            sample_ids=sample_ids,
        )
    return _get_all_without_similarity(
        session=session,
        collection_id=collection_id,
        pagination=pagination,
        filters=filters,
        sample_ids=sample_ids,
    )


def _get_all_with_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    distance_expr: ColumnElement[float],
    pagination: Paginated | None,
    filters: GroupFilter | None,
    sample_ids: list[UUID] | None,
) -> GroupViewsWithCount:
    """Get groups with similarity search - returns (GroupTable, float) tuples."""
    load_options = _get_load_options()

    samples_query = (
        select(GroupTable, distance_expr)
        .options(load_options)
        .join(GroupTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    samples_query = apply_similarity_join(
        query=samples_query,
        sample_id_column=col(GroupTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    total_count_query = (
        select(func.count())
        .select_from(GroupTable)
        .join(GroupTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    total_count_query = apply_similarity_join(
        query=total_count_query,
        sample_id_column=col(GroupTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    if sample_ids:
        samples_query = samples_query.where(col(GroupTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(GroupTable.sample_id).in_(sample_ids))

    samples_query = samples_query.order_by(distance_expr)

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()

    group_views = [
        GroupView(
            sample_id=r[0].sample_id,
            sample=SampleView.model_validate(r[0].sample),
            similarity_score=distance_to_similarity(r[1]),
        )
        for r in results
    ]

    return GroupViewsWithCount(
        samples=group_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
    )


def _get_all_without_similarity(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
    filters: GroupFilter | None,
    sample_ids: list[UUID] | None,
) -> GroupViewsWithCount:
    """Get groups without similarity search - returns GroupTable directly."""
    load_options = _get_load_options()

    samples_query = (
        select(GroupTable)
        .options(load_options)
        .join(GroupTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    total_count_query = (
        select(func.count())
        .select_from(GroupTable)
        .join(GroupTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    if sample_ids:
        samples_query = samples_query.where(col(GroupTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(GroupTable.sample_id).in_(sample_ids))

    samples_query = samples_query.order_by(col(GroupTable.sample_id).asc())

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    samples = session.exec(samples_query).all()

    group_views = [
        GroupView(
            sample_id=group.sample_id,
            sample=SampleView.model_validate(group.sample),
            similarity_score=None,
        )
        for group in samples
    ]

    return GroupViewsWithCount(
        samples=group_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
    )
