from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate
from lightly_studio.resolvers import dataset_resolver
from tests.helpers_resolvers import (
    create_dataset,
)


def test_create(test_db: Session) -> None:
    ds = dataset_resolver.create(
        session=test_db,
        dataset=DatasetCreate(name="my_dataset"),
    )
    assert ds.name == "my_dataset"

    # Creating a dataset with the same name should raise an error.
    with pytest.raises(ValueError, match="Dataset with name 'my_dataset' already exists."):
        dataset_resolver.create(
            session=test_db,
            dataset=DatasetCreate(name="my_dataset"),
        )


def test_get_by_id(test_db: Session) -> None:
    # Create two datasets
    ds1 = create_dataset(session=test_db, dataset_name="ds1")
    create_dataset(session=test_db, dataset_name="ds2")
    dataset_id = ds1.dataset_id

    # Fetch an existing dataset
    dataset_fetched = dataset_resolver.get_by_id(session=test_db, dataset_id=dataset_id)
    assert dataset_fetched is not None
    assert dataset_fetched.dataset_id == dataset_id
    assert dataset_fetched.name == "ds1"

    # Fetch a non-existing dataset
    dataset_fetched = dataset_resolver.get_by_id(session=test_db, dataset_id=UUID(int=123))
    assert dataset_fetched is None


def test_get_by_name(test_db: Session) -> None:
    # Create two datasets
    ds1 = create_dataset(session=test_db, dataset_name="ds1")
    create_dataset(session=test_db, dataset_name="ds2")

    # Exactly one dataset with the name exists
    dataset_fetched = dataset_resolver.get_by_name(session=test_db, name="ds1")
    assert dataset_fetched is not None
    assert dataset_fetched.dataset_id == ds1.dataset_id
    assert dataset_fetched.name == "ds1"

    # No dataset with the name exists
    dataset_fetched = dataset_resolver.get_by_name(session=test_db, name="non_existing")
    assert dataset_fetched is None
