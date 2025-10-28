from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import datasets_resolver
from tests.helpers_resolvers import (
    create_dataset,
)


def test_get_by_id(test_db: Session) -> None:
    # Create two datasets
    ds1 = create_dataset(session=test_db, dataset_name="ds1")
    create_dataset(session=test_db, dataset_name="ds2")
    dataset_id = ds1.dataset_id

    # Fetch an existing dataset
    dataset_fetched = datasets_resolver.get_by_id(session=test_db, dataset_id=dataset_id)
    assert dataset_fetched is not None
    assert dataset_fetched.dataset_id == dataset_id
    assert dataset_fetched.name == "ds1"

    # Fetch a non-existing dataset
    dataset_fetched = datasets_resolver.get_by_id(session=test_db, dataset_id=UUID(int=123))
    assert dataset_fetched is None
