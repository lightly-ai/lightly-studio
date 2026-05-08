from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_get_annotation_collections__success(db_session: Session) -> None:
    parent = create_collection(session=db_session)
    annotation_child_1 = create_collection(
        session=db_session,
        collection_name="ann_1",
        parent_collection_id=parent.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    annotation_child_2 = create_collection(
        session=db_session,
        collection_name="ann_2",
        parent_collection_id=parent.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    create_collection(
        session=db_session,
        collection_name="image_child",
        parent_collection_id=parent.collection_id,
        sample_type=SampleType.IMAGE,
    )

    result = collection_resolver.get_annotation_collections(
        session=db_session, parent_collection_id=parent.collection_id
    )

    assert [c.collection_id for c in result] == [
        annotation_child_1.collection_id,
        annotation_child_2.collection_id,
    ]


def test_get_annotation_collections__only_direct_children(db_session: Session) -> None:
    parent = create_collection(session=db_session)
    annotation_child = create_collection(
        session=db_session,
        collection_name="ann_child",
        parent_collection_id=parent.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    # Annotation grandchild — must not be returned when querying the root parent.
    create_collection(
        session=db_session,
        collection_name="ann_grandchild",
        parent_collection_id=annotation_child.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    result = collection_resolver.get_annotation_collections(
        session=db_session, parent_collection_id=parent.collection_id
    )

    assert [c.collection_id for c in result] == [annotation_child.collection_id]
