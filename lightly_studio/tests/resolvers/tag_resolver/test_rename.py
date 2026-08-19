from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_rename_tag(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag = create_tag(session=db_session, collection_id=collection_id)

    tag_renamed = tag_resolver.rename(session=db_session, tag_id=tag.tag_id, new_name="updated_tag")
    assert tag_renamed is not None
    assert tag_renamed.name == "updated_tag"


def test_rename_tag__preserves_sample_links(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag = create_tag(session=db_session, collection_id=collection_id)
    image_1 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="sample1.png"
    )
    image_2 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="sample2.png"
    )

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image_1.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image_2.sample)

    tag_renamed = tag_resolver.rename(session=db_session, tag_id=tag.tag_id, new_name="updated_tag")

    assert tag_renamed is not None
    assert tag_renamed.name == "updated_tag"
    assert tag_renamed.tag_id == tag.tag_id
    assert sorted(sample.sample_id for sample in tag_renamed.samples) == sorted(
        [image_1.sample.sample_id, image_2.sample.sample_id]
    )


def test_rename_tag__unique_tag_name(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag_1 = create_tag(session=db_session, collection_id=collection_id, tag_name="example_tag_1")
    tag_2 = create_tag(session=db_session, collection_id=collection_id, tag_name="some_other_tag")

    # renaming a tag to an existing name results in an IntegrityError
    with pytest.raises(IntegrityError):
        tag_resolver.rename(
            session=db_session,
            tag_id=tag_1.tag_id,
            new_name=tag_2.name,
        )
    db_session.rollback()


def test_rename_tag__unique_tag_name__preserves_original_tag_and_links(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag_1 = create_tag(session=db_session, collection_id=collection_id, tag_name="example_tag_1")
    tag_2 = create_tag(session=db_session, collection_id=collection_id, tag_name="some_other_tag")
    image_1 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="sample1.png"
    )
    image_2 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="sample2.png"
    )

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_1.tag_id, sample=image_1.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_1.tag_id, sample=image_2.sample)

    with pytest.raises(IntegrityError):
        tag_resolver.rename(
            session=db_session,
            tag_id=tag_1.tag_id,
            new_name=tag_2.name,
        )
    db_session.rollback()

    original_tag = tag_resolver.get_by_id(session=db_session, tag_id=tag_1.tag_id)
    assert original_tag is not None
    assert original_tag.name == "example_tag_1"
    assert sorted(sample.sample_id for sample in original_tag.samples) == sorted(
        [image_1.sample.sample_id, image_2.sample.sample_id]
    )


def test_rename_tag__unique_tag_name__different_kind(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    sample_tag = create_tag(
        session=db_session,
        collection_id=collection_id,
        kind="sample",
        tag_name="sample_tag_1",
    )
    annotation_tag = create_tag(
        session=db_session,
        collection_id=collection_id,
        kind="annotation",
        tag_name="annotation_tag_1",
    )

    # renaming a tag to an existing name but for a different kind is allowed
    tag_renamed = tag_resolver.rename(
        session=db_session,
        tag_id=sample_tag.tag_id,
        new_name=annotation_tag.name,
    )
    assert tag_renamed is not None
    assert tag_renamed.name == annotation_tag.name


def test_rename_tag__unknown_tag_returns_none(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    create_tag(session=db_session, collection_id=collection_id)

    tag_renamed = tag_resolver.rename(
        session=db_session,
        tag_id=uuid4(),
        new_name="unknown_tag",
    )
    assert tag_renamed is None
