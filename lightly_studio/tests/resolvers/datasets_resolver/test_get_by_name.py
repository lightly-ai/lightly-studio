from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import datasets_resolver
from tests.helpers_resolvers import (
    create_dataset,
)


def test_get_by_name(test_db: Session) -> None:
    # Create two datasets
    ds1 = create_dataset(session=test_db, dataset_name="ds1")
    create_dataset(session=test_db, dataset_name="ds2")

    # Exactly one dataset with the name exists
    dataset_fetched = datasets_resolver.get_by_name(session=test_db, name="ds1")
    assert dataset_fetched is not None
    assert dataset_fetched.dataset_id == ds1.dataset_id
    assert dataset_fetched.name == "ds1"

    # No dataset with the name exists
    dataset_fetched = datasets_resolver.get_by_name(session=test_db, name="non_existing")
    assert dataset_fetched is None
