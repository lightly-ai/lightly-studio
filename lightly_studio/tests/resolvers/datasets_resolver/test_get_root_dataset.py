"""Tests for datasets_resolver - get_dataset_hierarchy functionality."""

from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_get_root_dataset(
    db_session: Session,
) -> None:
    """Test dataset root retrieval.

    - A (root)
      - B
    """
    ds_a = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    ds_b = collection_resolver.create(
        session=db_session,
        dataset=CollectionCreate(
            name="ds_b", parent_dataset_id=ds_a.dataset_id, sample_type=SampleType.IMAGE
        ),
    )

    root_dataset = collection_resolver.get_dataset(session=db_session)
    assert root_dataset.dataset_id == ds_a.dataset_id

    root_dataset = collection_resolver.get_dataset(session=db_session, dataset_id=ds_a.dataset_id)
    assert root_dataset.dataset_id == ds_a.dataset_id

    root_dataset = collection_resolver.get_dataset(session=db_session, dataset_id=ds_b.dataset_id)
    assert root_dataset.dataset_id == ds_a.dataset_id


def test_get_root_dataset__multiple_root_datasets(
    db_session: Session,
) -> None:
    # First root tree
    first_root_dataset = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    # Second root tree
    second_root_dataset = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="ds_b", sample_type=SampleType.IMAGE)
    )

    root_dataset = collection_resolver.get_dataset(session=db_session)
    assert root_dataset.dataset_id == first_root_dataset.dataset_id

    root_dataset = collection_resolver.get_dataset(
        session=db_session, dataset_id=first_root_dataset.dataset_id
    )
    assert root_dataset.dataset_id == first_root_dataset.dataset_id

    root_dataset = collection_resolver.get_dataset(
        session=db_session, dataset_id=second_root_dataset.dataset_id
    )
    assert root_dataset.dataset_id == second_root_dataset.dataset_id


def test_get_root_dataset__no_dataset(
    db_session: Session,
) -> None:
    with pytest.raises(ValueError, match="No root dataset found. A root dataset must exist."):
        collection_resolver.get_dataset(session=db_session)

    not_found_dataset_id = uuid.uuid4()
    with pytest.raises(ValueError, match=f"Dataset with ID {not_found_dataset_id} not found."):
        collection_resolver.get_dataset(session=db_session, dataset_id=not_found_dataset_id)
