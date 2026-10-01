from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from tests.helpers_resolvers import create_collection, create_tag


def test_get_and_validate_sample_tags__returns_id_to_name_map(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    tag = create_tag(session=db_session, collection_id=collection.collection_id, tag_name="my-tag")

    result = annotation_count_helpers.get_and_validate_sample_tags(
        session=db_session,
        collection_id=collection.collection_id,
        sample_tag_ids=[tag.tag_id],
    )

    assert result == {tag.tag_id: "my-tag"}


def test_get_and_validate_sample_tags__raises_for_missing_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    missing_id = uuid4()

    with pytest.raises(ValueError, match="must be sample tags belonging to collection"):
        annotation_count_helpers.get_and_validate_sample_tags(
            session=db_session,
            collection_id=collection.collection_id,
            sample_tag_ids=[missing_id],
        )


def test_get_and_validate_sample_tags__raises_for_annotation_tag(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    annotation_tag = create_tag(
        session=db_session, collection_id=collection.collection_id, kind="annotation"
    )

    with pytest.raises(ValueError, match="must be sample tags belonging to collection"):
        annotation_count_helpers.get_and_validate_sample_tags(
            session=db_session,
            collection_id=collection.collection_id,
            sample_tag_ids=[annotation_tag.tag_id],
        )


def test_get_and_validate_sample_tags__raises_for_foreign_collection_tag(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    foreign_tag = create_tag(session=db_session, collection_id=other_collection.collection_id)

    with pytest.raises(ValueError, match="must be sample tags belonging to collection"):
        annotation_count_helpers.get_and_validate_sample_tags(
            session=db_session,
            collection_id=collection.collection_id,
            sample_tag_ids=[foreign_tag.tag_id],
        )
