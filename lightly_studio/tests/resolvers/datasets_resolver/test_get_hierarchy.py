"""Tests for datasets_resolver - get_dataset_hierarchy functionality."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_get_dataset_hierarchy(
    db_session: Session,
) -> None:
    """Test dataset hierarchy retrieval.

    Two trees are created:
    - A (root)
      - B
        - C
      - D
    - E (root)
      - F
    """
    # First tree
    ds_a = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    ds_b = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="ds_b", parent_collection_id=ds_a.collection_id, sample_type=SampleType.IMAGE
        ),
    )
    ds_c = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="ds_c", parent_collection_id=ds_b.collection_id, sample_type=SampleType.IMAGE
        ),
    )
    ds_d = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="ds_d", parent_collection_id=ds_a.collection_id, sample_type=SampleType.IMAGE
        ),
    )

    # Second tree
    ds_e = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="ds_e", sample_type=SampleType.IMAGE)
    )
    ds_f = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="ds_f", parent_collection_id=ds_e.collection_id, sample_type=SampleType.IMAGE
        ),
    )

    # Test first tree whole
    hierarchy = collection_resolver.get_hierarchy(
        session=db_session, root_collection_id=ds_a.collection_id
    )
    assert len(hierarchy) == 4
    hierarchy_ids = {ds.collection_id for ds in hierarchy}
    assert hierarchy_ids == {
        ds_a.collection_id,
        ds_b.collection_id,
        ds_c.collection_id,
        ds_d.collection_id,
    }

    # Test second tree whole
    hierarchy = collection_resolver.get_hierarchy(
        session=db_session, root_collection_id=ds_e.collection_id
    )
    assert len(hierarchy) == 2
    hierarchy_ids = {ds.collection_id for ds in hierarchy}
    assert hierarchy_ids == {ds_e.collection_id, ds_f.collection_id}

    # Test subtree
    hierarchy = collection_resolver.get_hierarchy(
        session=db_session, root_collection_id=ds_b.collection_id
    )
    assert len(hierarchy) == 2
    hierarchy_ids = {ds.collection_id for ds in hierarchy}
    assert hierarchy_ids == {ds_b.collection_id, ds_c.collection_id}

    # Test leaf node
    hierarchy = collection_resolver.get_hierarchy(
        session=db_session, root_collection_id=ds_f.collection_id
    )
    assert hierarchy == [ds_f]


def test_get_dataset_hierarchy__non_existent_dataset(
    db_session: Session,
) -> None:
    with pytest.raises(
        ValueError, match="Collection with id 00000000-0000-0000-0000-000000000000 not found."
    ):
        collection_resolver.get_hierarchy(
            session=db_session, root_collection_id=UUID("00000000-0000-0000-0000-000000000000")
        )
