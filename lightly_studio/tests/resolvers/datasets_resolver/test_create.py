from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate
from lightly_studio.models.sample_type import SampleType
from lightly_studio.resolvers import dataset_resolver


def test_create(test_db: Session) -> None:
    ds = dataset_resolver.create(
        session=test_db,
        dataset=DatasetCreate(name="my_dataset", sample_type=SampleType.IMAGE),
    )
    assert ds.name == "my_dataset"

    # Creating a dataset with the same name should raise an error.
    with pytest.raises(ValueError, match="Dataset with name 'my_dataset' already exists."):
        dataset_resolver.create(
            session=test_db,
            dataset=DatasetCreate(name="my_dataset", sample_type=SampleType.IMAGE),
        )
