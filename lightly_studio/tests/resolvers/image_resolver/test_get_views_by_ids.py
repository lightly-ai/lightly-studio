"""Tests for get_views_by_ids resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.models.image import ImageView
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_get_views_by_ids(db_session: Session) -> None:
    """Test getting views for multiple images."""
    collection = create_collection(session=db_session)
    image1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image1.png",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image2.png",
    )

    result = image_resolver.get_views_by_ids(
        session=db_session, sample_ids=[image1.sample_id, image2.sample_id]
    )

    assert len(result) == 2
    assert all(isinstance(view, ImageView) for view in result)
    assert result[0].sample_id == image1.sample_id
    assert result[0].file_path_abs == "/path/to/image1.png"
    assert result[1].sample_id == image2.sample_id
    assert result[1].file_path_abs == "/path/to/image2.png"


def test_get_views_by_ids__single_id(db_session: Session) -> None:
    """Test getting view for a single image using get_views_by_ids."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image.png",
    )

    result = image_resolver.get_views_by_ids(session=db_session, sample_ids=[image.sample_id])

    assert len(result) == 1
    assert isinstance(result[0], ImageView)
    assert result[0].sample_id == image.sample_id
    assert result[0].file_path_abs == "/path/to/image.png"


def test_get_views_by_ids__not_found(db_session: Session) -> None:
    """Test getting views for non-existent images raises ValueError."""
    from uuid import uuid4

    non_existent_id = uuid4()

    with pytest.raises(ValueError, match="Images with sample_ids.*not found"):
        image_resolver.get_views_by_ids(session=db_session, sample_ids=[non_existent_id])


def test_get_views_by_ids__empty_list(db_session: Session) -> None:
    """Test getting views with empty sample_ids list raises ValueError."""
    with pytest.raises(ValueError, match="Images with sample_ids.*not found"):
        image_resolver.get_views_by_ids(session=db_session, sample_ids=[])
