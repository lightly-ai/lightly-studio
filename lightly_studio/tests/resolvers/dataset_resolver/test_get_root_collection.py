"""Tests for get_root_collection resolver."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver, dataset_resolver


def test_get_root_collection(
    db_session: Session,
) -> None:
    """Test root collection retrieval."""
    # First tree
    coll_a = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="coll_a", sample_type=SampleType.IMAGE)
    )
    collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="coll_b", parent_collection_id=coll_a.collection_id, sample_type=SampleType.IMAGE
        ),
    )

    # Second tree
    coll_c = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="coll_c", sample_type=SampleType.IMAGE)
    )

    # Test first tree
    root = dataset_resolver.get_root_collection(session=db_session, dataset_id=coll_a.dataset_id)
    assert root.collection_id == coll_a.collection_id
    assert root.dataset_id == coll_a.dataset_id

    # Test second tree
    root = dataset_resolver.get_root_collection(session=db_session, dataset_id=coll_c.dataset_id)
    assert root.collection_id == coll_c.collection_id
    assert root.dataset_id == coll_c.dataset_id


def test_get_root_collection__non_existent_dataset(
    db_session: Session,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"Dataset with id 00000000-0000-0000-0000-000000000000 not found\.",
    ):
        dataset_resolver.get_root_collection(
            session=db_session, dataset_id=UUID("00000000-0000-0000-0000-000000000000")
        )
