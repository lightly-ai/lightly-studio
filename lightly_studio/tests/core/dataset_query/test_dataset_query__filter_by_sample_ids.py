from __future__ import annotations

import pytest
from sqlmodel import Session, select

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection


def test_filter_by_sample_ids__called_twice__raises(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    query = DatasetQuery(dataset=collection, session=db_session)
    subquery = select(SampleTable.sample_id)

    query.filter_by_sample_ids(subquery)

    with pytest.raises(ValueError, match="filter_by_sample_ids\\(\\) can only be called once"):
        query.filter_by_sample_ids(subquery)
