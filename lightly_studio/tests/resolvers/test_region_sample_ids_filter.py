from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.region_sample_ids_filter import RegionSampleIdsFilter
from lightly_studio.type_definitions import QueryType
from tests.helpers_resolvers import create_collection, create_image


class _RegionFilter(RegionSampleIdsFilter):
    """Minimal filter exposing the mixin's region predicate on ``SampleTable``."""

    def apply(self, query: QueryType) -> QueryType:
        return self._apply_region_sample_ids_filter(
            query, sample_id_column=col(SampleTable.sample_id)
        )


def test_apply__none_does_not_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="a.png"
    )

    query = _RegionFilter(region_sample_ids=None).apply(select(SampleTable.sample_id))

    assert set(db_session.exec(query).all()) == {image.sample_id}


def test_apply__empty_list_matches_nothing(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    create_image(session=db_session, collection_id=collection.collection_id, file_path_abs="a.png")

    query = _RegionFilter(region_sample_ids=[]).apply(select(SampleTable.sample_id))

    assert db_session.exec(query).all() == []


def test_apply__restricts_to_region_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    in_region = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="in.png"
    )
    create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="out.png"
    )

    query = _RegionFilter(region_sample_ids=[in_region.sample_id]).apply(
        select(SampleTable.sample_id)
    )

    assert set(db_session.exec(query).all()) == {in_region.sample_id}
