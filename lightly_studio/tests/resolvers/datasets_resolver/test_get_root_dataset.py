"""Tests for datasets_resolver - get_dataset_hierarchy functionality."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate, SampleType
from lightly_studio.resolvers import dataset_resolver


def test_get_root_dataset(
    db_session: Session,
) -> None:
    """Test dataset root retrieval.

    - A (root)
      - B
    """
    ds_a = dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(
            name="ds_b", parent_dataset_id=ds_a.dataset_id, sample_type=SampleType.IMAGE
        ),
    )

    root_dataset = dataset_resolver.get_root_dataset(session=db_session)
    assert root_dataset.dataset_id == ds_a.dataset_id


def test_get_root_dataset__multiple_root_datasets(
    db_session: Session,
) -> None:
    # First root tree
    first_root_dataset = dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="ds_a", sample_type=SampleType.IMAGE)
    )
    # Second root tree
    dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="ds_b", sample_type=SampleType.IMAGE)
    )

    root_dataset = dataset_resolver.get_root_dataset(session=db_session)
    assert root_dataset.dataset_id == first_root_dataset.dataset_id


def test_get_root_dataset__no_dataset(
    db_session: Session,
) -> None:
    with pytest.raises(ValueError, match="No root dataset found. A root dataset must exist."):
        dataset_resolver.get_root_dataset(session=db_session)
