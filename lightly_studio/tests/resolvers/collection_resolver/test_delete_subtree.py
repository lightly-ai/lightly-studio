"""Tests for the delete_subtree collection resolver function."""

import uuid

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_caption,
    create_collection,
    create_image,
    create_source_annotations,
)


def test_delete_subtree(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotations = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=2
    )
    source_id = annotations[0].annotation_collection_id
    caption = create_caption(
        session=db_session, collection_id=source_id, parent_sample_id=annotations[0].sample_id
    )
    create_caption(
        session=db_session,
        collection_id=caption.sample.collection_id,
        parent_sample_id=caption.sample_id,
    )

    deleted_count = collection_resolver.delete_subtree(session=db_session, collection_id=source_id)

    assert deleted_count == 2
    assert collection_resolver.get_subtree_ids(session=db_session, collection_id=source_id) == []


def test_delete_subtree__unknown_collection(db_session: Session) -> None:
    deleted_count = collection_resolver.delete_subtree(
        session=db_session, collection_id=uuid.uuid4()
    )

    assert deleted_count == 0
