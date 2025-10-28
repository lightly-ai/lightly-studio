"""Tests for datasets_resolver - get_dataset_hierarchy functionality."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate
from lightly_studio.resolvers import dataset_resolver, datasets_resolver


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
    ds_a = dataset_resolver.create(session=db_session, dataset=DatasetCreate(name="ds_a"))
    ds_b = dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(name="ds_b", parent_dataset_id=ds_a.dataset_id),
    )
    ds_c = dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(name="ds_c", parent_dataset_id=ds_b.dataset_id),
    )
    ds_d = dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(name="ds_d", parent_dataset_id=ds_a.dataset_id),
    )

    # Second tree
    ds_e = dataset_resolver.create(session=db_session, dataset=DatasetCreate(name="ds_e"))
    ds_f = dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(name="ds_f", parent_dataset_id=ds_e.dataset_id),
    )

    # Test first tree whole
    hierarchy = datasets_resolver.get_hierarchy(session=db_session, root_dataset_id=ds_a.dataset_id)
    assert len(hierarchy) == 4
    hierarchy_ids = {ds.dataset_id for ds in hierarchy}
    assert hierarchy_ids == {ds_a.dataset_id, ds_b.dataset_id, ds_c.dataset_id, ds_d.dataset_id}

    # Test second tree whole
    hierarchy = datasets_resolver.get_hierarchy(session=db_session, root_dataset_id=ds_e.dataset_id)
    assert len(hierarchy) == 2
    hierarchy_ids = {ds.dataset_id for ds in hierarchy}
    assert hierarchy_ids == {ds_e.dataset_id, ds_f.dataset_id}

    # Test subtree
    hierarchy = datasets_resolver.get_hierarchy(session=db_session, root_dataset_id=ds_b.dataset_id)
    assert len(hierarchy) == 2
    hierarchy_ids = {ds.dataset_id for ds in hierarchy}
    assert hierarchy_ids == {ds_b.dataset_id, ds_c.dataset_id}

    # Test leaf node
    hierarchy = datasets_resolver.get_hierarchy(session=db_session, root_dataset_id=ds_f.dataset_id)
    assert hierarchy == [ds_f]


def test_get_dataset_hierarchy__non_existent_dataset(
    db_session: Session,
) -> None:
    with pytest.raises(
        ValueError, match="Dataset with id 00000000-0000-0000-0000-000000000000 not found."
    ):
        datasets_resolver.get_hierarchy(
            session=db_session, root_dataset_id=UUID("00000000-0000-0000-0000-000000000000")
        )
