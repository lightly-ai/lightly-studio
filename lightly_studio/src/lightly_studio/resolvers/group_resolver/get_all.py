"""Get groups ordered by creation time."""

from __future__ import annotations

from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.group import GroupTable, GroupView, GroupViewsWithCount
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.resolvers import group_resolver
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter


def get_all(
    session: Session,
    pagination: Paginated | None,
    filters: GroupFilter | None,
) -> GroupViewsWithCount:
    """Retrieve groups ordered by creation time.

    Groups are returned in ascending order by created_at timestamp, and all similarity
    scores in the response are set to None.

    Args:
        session: Database session for executing queries.
        pagination: Optional pagination parameters (offset and limit) for results.
        filters: Optional GroupFilter instance to apply additional filtering criteria.

    Returns:
        GroupViewsWithCount containing:
        - samples: List of GroupView objects with similarity_score set to None
        - total_count: Total number of groups matching the query (before pagination)
        - next_cursor: Cursor for pagination to fetch the next page of results
    """
    load_options = _get_load_options()

    samples_query = select(GroupTable).options(load_options).join(GroupTable.sample)

    total_count_query = select(func.count()).select_from(GroupTable).join(GroupTable.sample)

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    samples_query = samples_query.order_by(col(SampleTable.created_at).asc())
    group_collection_id = (
        filters.sample_filter.collection_id
        if filters and filters.sample_filter and filters.sample_filter.collection_id
        else None
    )

    if group_collection_id is None:
        raise ValueError("Collection ID must be provided in filters to fetch groups.")

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    samples = session.exec(samples_query).all()

    # Fetch first sample (image or video) for each group
    group_sample_ids = [group.sample_id for group in samples]
    group_previews = group_resolver.get_group_previews(
        session=session,
        group_sample_ids=group_sample_ids,
        group_collection_id=group_collection_id,
    )
    group_sample_counts = group_resolver.get_group_sample_counts(
        session=session, group_sample_ids=group_sample_ids
    )

    group_views = [
        GroupView(
            sample_id=group.sample_id,
            sample=SampleView.model_validate(group.sample),
            similarity_score=None,
            group_preview=group_previews.get(group.sample_id),
            sample_count=group_sample_counts.get(group.sample_id, 0),
        )
        for group in samples
    ]

    return GroupViewsWithCount(
        samples=group_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination=pagination, total_count=total_count),
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
