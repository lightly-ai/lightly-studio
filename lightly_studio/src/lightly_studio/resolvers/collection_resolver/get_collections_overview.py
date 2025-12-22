"""Handler for database operations related to fetching root collections with details."""

from __future__ import annotations

from sqlmodel import Session, col, func, select

from lightly_studio.models.collection import CollectionOverviewView, CollectionTable
from lightly_studio.models.sample import SampleTable


def get_collections_overview(session: Session) -> list[CollectionOverviewView]:
    """Get root collections with detailed metadata including sample counts."""
    collections_query = (
        select(  # type: ignore[call-overload]
            CollectionTable.collection_id,
            CollectionTable.name,
            CollectionTable.sample_type,
            CollectionTable.created_at,
            func.count(col(SampleTable.collection_id)).label("sample_count"),
        )
        .outerjoin(SampleTable)
        .where(col(CollectionTable.parent_collection_id).is_(None))
        .group_by(
            CollectionTable.collection_id,
            CollectionTable.name,
            CollectionTable.sample_type,
            CollectionTable.created_at,
        )
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
        for row in session.exec(collections_query).all()
    ]
