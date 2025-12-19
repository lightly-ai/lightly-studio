"""Handler for database operations related to collections."""

from __future__ import annotations

from sqlmodel import Session, func, select

from lightly_studio.models.collection import CollectionTable, CollectionViewWithCount
from lightly_studio.models.sample import SampleTable


def get_collection_details(
    session: Session, collection: CollectionTable
) -> CollectionViewWithCount:
    """Convert a CollectionTable to CollectionViewWithCount with computed sample count."""
    sample_count = (
        session.exec(
            select(func.count("*")).where(SampleTable.collection_id == collection.collection_id)
        ).one()
        or 0
    )
    return CollectionViewWithCount(
        collection_id=collection.collection_id,
        parent_collection_id=collection.parent_collection_id,
        sample_type=collection.sample_type,
        name=collection.name,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        total_sample_count=sample_count,
    )
