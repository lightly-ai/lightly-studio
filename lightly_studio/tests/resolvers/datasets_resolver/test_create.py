from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_create(test_db: Session) -> None:
    ds = collection_resolver.create(
        session=test_db,
        collection=CollectionCreate(name="my_dataset", sample_type=SampleType.IMAGE),
    )
    assert ds.name == "my_dataset"

    # Creating a dataset with the same name should raise an error.
    with pytest.raises(ValueError, match="Dataset with name 'my_dataset' already exists."):
        collection_resolver.create(
            session=test_db,
            collection=CollectionCreate(name="my_dataset", sample_type=SampleType.IMAGE),
        )
