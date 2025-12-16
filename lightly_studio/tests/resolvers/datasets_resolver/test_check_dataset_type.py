from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_check_dataset_type(db_session: Session) -> None:
    dataset = collection_resolver.create(
        session=db_session,
        dataset=CollectionCreate(name="test_dataset", sample_type=SampleType.IMAGE),
    )

    # Matching type does not raise
    collection_resolver.check_dataset_type(
        session=db_session,
        dataset_id=dataset.dataset_id,
        expected_type=SampleType.IMAGE,
    )

    # Non-matching type raises ValueError
    with pytest.raises(ValueError, match="is having sample type 'image', expected 'video'"):
        collection_resolver.check_dataset_type(
            session=db_session,
            dataset_id=dataset.dataset_id,
            expected_type=SampleType.VIDEO,
        )

    # Non-existing dataset raises ValueError
    with pytest.raises(
        ValueError, match="Dataset with id 00000000-0000-0000-0000-000000000000 not found."
    ):
        collection_resolver.check_dataset_type(
            session=db_session,
            dataset_id=UUID("00000000-0000-0000-0000-000000000000"),
            expected_type=SampleType.IMAGE,
        )
