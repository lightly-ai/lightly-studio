"""Handler for database operations related to fetching root collections with details."""

from __future__ import annotations

from sqlalchemy import select
from sqlmodel import Session, col, func

from lightly_studio.models.collection import CollectionOverviewView, CollectionTable
from lightly_studio.models.sample import SampleTable


def get_collections_overview(session: Session) -> list[CollectionOverviewView]:
    """Get root collections with detailed metadata including sample counts."""
    sample_count = (
        select(func.count())
        .select_from(SampleTable)
        .where(col(SampleTable.collection_id) == col(CollectionTable.collection_id))
        .scalar_subquery()
        .label("sample_count")
    )
    collections_query = (
        select(
            col(CollectionTable.collection_id),
            col(CollectionTable.name),
            col(CollectionTable.sample_type),
            col(CollectionTable.created_at),
            sample_count,
        )
        .where(col(CollectionTable.parent_collection_id).is_(None))
        .order_by(col(CollectionTable.created_at).desc())
    )

    return [
        CollectionOverviewView(
            collection_id=row.collection_id,
            name=row.name,
            sample_type=row.sample_type,
            created_at=row.created_at,
            total_sample_count=row.sample_count,
        )
        for row in session.execute(collections_query)
    ]
