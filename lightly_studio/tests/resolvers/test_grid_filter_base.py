from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.type_definitions import QueryType
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


class _AnnotationParentFilter(GridFilterBase):
    """Test-only filter exercising ``GridFilterBase`` independently of any real filter.

    Its base select joins ``SampleTable.annotations``, yielding one row per annotation,
    so a parent sample with several annotations appears multiple times before the base
    template applies ``distinct``.
    """

    def apply(self, query: QueryType) -> QueryType:
        return query

    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        return select(SampleTable.sample_id).join(SampleTable.annotations)


def _create_annotated_image(
    session: Session,
    collection_id: UUID,
    file_path_abs: str,
    annotation_count: int = 1,
) -> UUID:
    """Create an image with ``annotation_count`` annotations and return its sample id."""
    image = create_image(session=session, collection_id=collection_id, file_path_abs=file_path_abs)
    label = create_annotation_label(session=session, root_collection_id=collection_id)
    for _ in range(annotation_count):
        create_annotation(
            session=session,
            collection_id=collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
    return image.sample_id


def test_build_sample_ids_query__scopes_to_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    sample_id = _create_annotated_image(
        db_session, collection.collection_id, file_path_abs="in.png"
    )
    _create_annotated_image(db_session, other_collection.collection_id, file_path_abs="out.png")

    query = _AnnotationParentFilter().build_sample_ids_query(collection_id=collection.collection_id)

    assert set(db_session.exec(query).all()) == {sample_id}


def test_build_sample_ids_query__deduplicates_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    sample_id = _create_annotated_image(
        db_session, collection.collection_id, file_path_abs="img.png", annotation_count=2
    )

    query = _AnnotationParentFilter().build_sample_ids_query(collection_id=collection.collection_id)

    # The two annotations would yield two identical rows without ``distinct``.
    assert db_session.exec(query).all() == [sample_id]
