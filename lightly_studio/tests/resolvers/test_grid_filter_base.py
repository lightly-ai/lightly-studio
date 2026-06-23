from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.type_definitions import QueryType
from tests.helpers_resolvers import (
    create_caption,
    create_collection,
    create_image,
)


class _CaptionParentFilter(GridFilterBase):
    """Test filter whose base select joins ``SampleTable.captions``.

    The join yields one row per caption, so a sample with several captions appears
    multiple times before the base template applies ``distinct``.
    """

    def apply(self, query: QueryType) -> QueryType:
        return query

    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        return select(SampleTable.sample_id).join(SampleTable.captions)


def test_build_sample_ids_query__scopes_to_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="in.png"
    )
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image.sample_id,
    )

    other_image = create_image(
        session=db_session, collection_id=other_collection.collection_id, file_path_abs="out.png"
    )
    create_caption(
        session=db_session,
        collection_id=other_collection.collection_id,
        parent_sample_id=other_image.sample_id,
    )

    query = _CaptionParentFilter().build_sample_ids_query(collection_id=collection.collection_id)

    assert set(db_session.exec(query).all()) == {image.sample_id}


def test_build_sample_ids_query__deduplicates_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="img.png"
    )
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image.sample_id,
        text="first caption",
    )
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image.sample_id,
        text="second caption",
    )

    query = _CaptionParentFilter().build_sample_ids_query(collection_id=collection.collection_id)

    # The two captions would yield two identical rows without ``distinct``.
    assert db_session.exec(query).all() == [image.sample_id]
