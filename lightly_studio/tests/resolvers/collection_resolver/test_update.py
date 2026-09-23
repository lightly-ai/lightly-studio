from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_update__duplicate_name(db_session: Session) -> None:
    create_collection(session=db_session, collection_name="ds1")
    ds2 = create_collection(session=db_session, collection_name="ds2")

    with pytest.raises(ValueError, match=r"A collection named 'ds1' already exists."):
        collection_resolver.update(
            session=db_session,
            collection_id=ds2.collection_id,
            collection_input=CollectionCreate(name="ds1", sample_type=SampleType.IMAGE),
        )
    assert ds2.name == "ds2"
