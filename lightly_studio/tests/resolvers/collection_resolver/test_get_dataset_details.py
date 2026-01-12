"""Tests for collections_resolver - get_collection_details functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_get_collection_details(
    db_session: Session,
) -> None:
    """Test that get_collection_details returns correct sample count."""
    collection = create_collection(session=db_session, collection_name="test_collection")

    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image1.jpg",
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image2.jpg",
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image3.jpg",
    )

    result = collection_resolver.get_collection_details(session=db_session, collection=collection)

    assert result.collection_id == collection.collection_id
    assert result.name == collection.name
    assert result.created_at == collection.created_at
    assert result.updated_at == collection.updated_at
    assert result.total_sample_count == 3


def test_get_collection_details__empty_collection(
    db_session: Session,
) -> None:
    """Test that get_collection_details returns zero for empty collection."""
    collection = create_collection(session=db_session, collection_name="empty_collection")

    result = collection_resolver.get_collection_details(session=db_session, collection=collection)

    assert result.total_sample_count == 0
    assert result.collection_id == collection.collection_id
    assert result.name == collection.name
