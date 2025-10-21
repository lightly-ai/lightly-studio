from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.tag import TagCreate, TagUpdate
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_dataset, create_tag


def test_create_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag = create_tag(session=test_db, dataset_id=dataset_id, tag_name="example_tag")
    assert tag.name == "example_tag"


def test_create_tag__unique_tag_name(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    create_tag(session=test_db, dataset_id=dataset_id, tag_name="example_tag")

    # trying to create a tag with the same name results in an IntegrityError
    with pytest.raises(IntegrityError):
        tag_resolver.create(
            session=test_db,
            tag=TagCreate(
                dataset_id=dataset_id,
                name="example_tag",
                kind="sample",
            ),
        )


def test_read_tags(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    tag_1 = create_tag(session=test_db, dataset_id=dataset_id, tag_name="tag_1")
    create_tag(session=test_db, dataset_id=dataset_id, tag_name="tag_2")
    create_tag(session=test_db, dataset_id=dataset_id, tag_name="tag_3")

    # get all tags of a dataset
    tags = tag_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)
    assert len(tags) == 3
    # check order
    tag = tags[0]
    assert tag.tag_id == tag_1.tag_id
    assert tag.name == tag_1.name


def test_read_tags__paginated(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    total = 10
    chunk_size = total // 2
    for i in range(total):
        create_tag(session=test_db, dataset_id=dataset_id, tag_name=f"example_tag_{i}")

    # get first chunk/page
    page_1 = tag_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset.dataset_id,
        offset=0,
        limit=chunk_size,
    )
    assert len(page_1) == chunk_size

    # get second chunk/page
    page_2 = tag_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset.dataset_id,
        offset=5,
        limit=chunk_size,
    )
    assert len(page_2) == chunk_size

    # assert that the two chunks are different
    assert page_1 != page_2
    assert page_1[0].name != page_2[0].name


def test_read_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    tag = create_tag(session=test_db, dataset_id=dataset_id)

    tag_read = tag_resolver.get_by_id(session=test_db, tag_id=tag.tag_id)
    assert tag_read is not None
    assert tag_read.tag_id == tag.tag_id
    assert tag_read.name == "example_tag"


def test_update_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    tag = create_tag(session=test_db, dataset_id=dataset_id)

    data_update = TagUpdate(name="updated_tag")
    tag_updated = tag_resolver.update(session=test_db, tag_id=tag.tag_id, tag_data=data_update)
    # assert tag name changed.
    assert tag_updated is not None
    assert tag_updated.name == data_update.name


def test_update_tag__unique_tag_name(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    tag_1 = create_tag(session=test_db, dataset_id=dataset_id, tag_name="example_tag_1")
    tag_2 = create_tag(session=test_db, dataset_id=dataset_id, tag_name="some_other_tag")

    # updating a tag with a name that already exists results in 409
    # trying to create a tag with the same name results in an IntegrityError
    with pytest.raises(IntegrityError):
        tag_resolver.update(
            session=test_db,
            tag_id=tag_1.tag_id,
            tag_data=TagUpdate(name=tag_2.name),
        )


def test_update_tag__unique_tag_name__different_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    sample_tag = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        kind="sample",
        tag_name="sample_tag_1",
    )
    annotation_tag = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        kind="annotation",
        tag_name="annotation_tag_1",
    )

    # updating a tag with an existing name but for a different kind is allowed
    tag_updated = tag_resolver.update(
        session=test_db,
        tag_id=sample_tag.tag_id,
        tag_data=TagUpdate(name=annotation_tag.name),
    )
    # assert tag name changed.
    assert tag_updated is not None
    assert tag_updated.name == annotation_tag.name


def test_update_tag__unknown_tag_404(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    create_tag(session=test_db, dataset_id=dataset_id)

    # updating a unknown tag results in 404
    tag_updated = tag_resolver.update(
        session=test_db,
        tag_id=uuid4(),
        tag_data=TagUpdate(name="unknown_tag"),
    )
    assert tag_updated is None


def test_delete_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    tag = create_tag(session=test_db, dataset_id=dataset_id)

    # Delete the tag
    tag_resolver.delete(session=test_db, tag_id=tag.tag_id)

    # assert tag was deleted
    tag_deleted = tag_resolver.get_by_id(session=test_db, tag_id=tag.tag_id)
    assert tag_deleted is None


def test_get_or_create_sample_tag_by_name(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create an existing tag
    existing_tag = create_tag(session=test_db, dataset_id=dataset_id, tag_name="existing_tag")

    # Case 1: Get existing tag
    result_tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=test_db, dataset_id=dataset_id, tag_name="existing_tag"
    )
    assert result_tag.tag_id == existing_tag.tag_id
    assert result_tag.name == "existing_tag"

    # Case 2: Create new tag
    new_tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=test_db, dataset_id=dataset_id, tag_name="new_tag"
    )
    assert new_tag.tag_id != existing_tag.tag_id
    assert new_tag.name == "new_tag"
    assert new_tag.dataset_id == dataset_id
    assert new_tag.kind == "sample"
