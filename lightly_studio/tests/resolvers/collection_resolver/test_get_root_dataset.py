"""Tests for collections_resolver - get_collection_hierarchy functionality."""

from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_get_root_collection(
    db_session: Session,
) -> None:
    """Test collection root retrieval.

    - A (root)
      - B
    """
    ds_a = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    ds_b = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="ds_b", parent_collection_id=ds_a.collection_id, sample_type=SampleType.IMAGE
        ),
    )

    root_collection = collection_resolver.get_dataset(session=db_session)
    assert root_collection.collection_id == ds_a.collection_id

    root_collection = collection_resolver.get_dataset(
        session=db_session, collection_id=ds_a.collection_id
    )
    assert root_collection.collection_id == ds_a.collection_id

    root_collection = collection_resolver.get_dataset(
        session=db_session, collection_id=ds_b.collection_id
    )
    assert root_collection.collection_id == ds_a.collection_id


def test_get_root_collection__multiple_root_collections(
    db_session: Session,
) -> None:
    # First root tree
    first_root_collection = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    # Second root tree
    second_root_collection = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="ds_b", sample_type=SampleType.IMAGE)
    )

    root_collection = collection_resolver.get_dataset(session=db_session)
    assert root_collection.collection_id == first_root_collection.collection_id

    root_collection = collection_resolver.get_dataset(
        session=db_session, collection_id=first_root_collection.collection_id
    )
    assert root_collection.collection_id == first_root_collection.collection_id

    root_collection = collection_resolver.get_dataset(
        session=db_session, collection_id=second_root_collection.collection_id
    )
    assert root_collection.collection_id == second_root_collection.collection_id


def test_get_root_collection__no_collection(
    db_session: Session,
) -> None:
    with pytest.raises(ValueError, match="No root collection found. A root collection must exist."):
        collection_resolver.get_dataset(session=db_session)

    not_found_collection_id = uuid.uuid4()
    with pytest.raises(
        ValueError, match=f"Collection with ID {not_found_collection_id} not found."
    ):
        collection_resolver.get_dataset(session=db_session, collection_id=not_found_collection_id)
