from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.tag import TagCreate, TagUpdate
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_dataset, create_image, create_tag


def test_create_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag = create_tag(session=test_db, dataset_id=dataset_id, tag_name="example_tag")
    assert tag.name == "example_tag"


def test_create_tag__unique_tag_name(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    create_tag(session=test_db, dataset_id=dataset_id, tag_name="example_tag")

    # trying to create a tag with the same name results in an IntegrityError
    with pytest.raises(IntegrityError):
        tag_resolver.create(
            session=test_db,
            tag=TagCreate(
                collection_id=dataset_id,
                name="example_tag",
                kind="sample",
            ),
        )


def test_read_tags(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

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
    dataset_id = dataset.collection_id

    total = 10
    chunk_size = total // 2
    for i in range(total):
        create_tag(session=test_db, dataset_id=dataset_id, tag_name=f"example_tag_{i}")

    # get first chunk/page
    page_1 = tag_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset.collection_id,
        offset=0,
        limit=chunk_size,
    )
    assert len(page_1) == chunk_size

    # get second chunk/page
    page_2 = tag_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset.collection_id,
        offset=5,
        limit=chunk_size,
    )
    assert len(page_2) == chunk_size

    # assert that the two chunks are different
    assert page_1 != page_2
    assert page_1[0].name != page_2[0].name


def test_read_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    tag = create_tag(session=test_db, dataset_id=dataset_id)

    tag_read = tag_resolver.get_by_id(session=test_db, tag_id=tag.tag_id)
    assert tag_read is not None
    assert tag_read.tag_id == tag.tag_id
    assert tag_read.name == "example_tag"


def test_update_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    tag = create_tag(session=test_db, dataset_id=dataset_id)

    data_update = TagUpdate(name="updated_tag")
    tag_updated = tag_resolver.update(session=test_db, tag_id=tag.tag_id, tag_data=data_update)
    # assert tag name changed.
    assert tag_updated is not None
    assert tag_updated.name == data_update.name


def test_update_tag__unique_tag_name(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

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
    dataset_id = dataset.collection_id

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
    dataset_id = dataset.collection_id

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
    dataset_id = dataset.collection_id

    tag = create_tag(session=test_db, dataset_id=dataset_id)

    # Delete the tag
    tag_resolver.delete(session=test_db, tag_id=tag.tag_id)

    # assert tag was deleted
    tag_deleted = tag_resolver.get_by_id(session=test_db, tag_id=tag.tag_id)
    assert tag_deleted is None


def test_get_or_create_sample_tag_by_name(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

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
    assert new_tag.collection_id == dataset_id
    assert new_tag.kind == "sample"


def test_add_tag_to_sample(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag = create_tag(session=test_db, dataset_id=dataset_id, kind="sample")
    image = create_image(session=test_db, dataset_id=dataset_id)

    # add sample to tag
    tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=image.sample)

    assert image.sample.tags.index(tag) == 0


def test_add_tag_to_sample__ensure_correct_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag_with_wrong_kind = create_tag(session=test_db, dataset_id=dataset_id, kind="annotation")
    image = create_image(session=test_db, dataset_id=dataset_id)

    # adding sample to tag with wrong kind raises ValueError
    with pytest.raises(ValueError, match="is not of kind 'sample'"):
        tag_resolver.add_tag_to_sample(
            session=test_db, tag_id=tag_with_wrong_kind.tag_id, sample=image.sample
        )


def test_remove_sample_from_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag = create_tag(session=test_db, dataset_id=dataset_id, kind="sample")
    image = create_image(session=test_db, dataset_id=dataset_id)

    # add sample to tag
    tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=image.sample)
    assert len(image.sample.tags) == 1
    assert image.sample.tags.index(tag) == 0

    # remove sample to tag
    tag_resolver.remove_tag_from_sample(session=test_db, tag_id=tag.tag_id, sample=image.sample)
    assert len(image.sample.tags) == 0
    with pytest.raises(ValueError, match="is not in list"):
        image.sample.tags.index(tag)


def test_add_and_remove_sample_ids_to_tag_id(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_all",
        kind="sample",
    )
    tag_2 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_odd",
        kind="sample",
    )

    total_samples = 10
    images = []
    for i in range(total_samples):
        image = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"sample{i}.png",
        )
        images.append(image)

    # add samples to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # add every odd samples to tag_2
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i % 2 == 1],
    )

    # ensure all samples were added to the correct tags
    for i, image in enumerate(images):
        assert tag_1 in image.sample.tags
        if i % 2 == 1:
            assert tag_2 in image.sample.tags

    # ensure the correct number of samples were added to each tag
    assert len(tag_1.samples) == total_samples
    assert len(tag_2.samples) == total_samples / 2

    # Remove the *same* even indexed samples we added earlier,
    # but computed from the original `samples` list so ordering is stable.
    tag_resolver.remove_sample_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[s.sample_id for i, s in enumerate(images) if i % 2 == 0],
    )

    assert len(tag_1.samples) == total_samples / 2
    assert len(tag_2.samples) == total_samples / 2

    tag_1_samples_sorted = sorted(tag_1.samples, key=lambda s: s.sample_id)
    tag_2_samples_sorted = sorted(tag_2.samples, key=lambda s: s.sample_id)
    assert tag_1_samples_sorted == tag_2_samples_sorted


def test_add_and_remove_sample_ids_to_tag_id__twice_same_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_all",
        kind="sample",
    )

    total_samples = 10
    images = []
    for i in range(total_samples):
        image = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"sample{i}.png",
        )
        images.append(image)

    # add samples to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # adding the same samples to tag_1 does not create an error
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # ensure all samples were added once
    assert len(tag_1.samples) == total_samples

    # remove samples from
    tag_resolver.remove_sample_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )
    # removing the same samples to tag_1 does not create an error
    tag_resolver.remove_sample_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # ensure all samples were removed again
    assert len(tag_1.samples) == 0


def test_add_and_remove_sample_ids_to_tag_id__ensure_correct_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag_with_wrong_kind = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_with_wrong_kind",
        kind="annotation",
    )

    samples = [
        create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs="sample.png",
        )
    ]

    # adding samples to tag with wrong kind raises ValueError
    with pytest.raises(ValueError, match="is not of kind 'sample'"):
        tag_resolver.add_sample_ids_to_tag_id(
            session=test_db,
            tag_id=tag_with_wrong_kind.tag_id,
            sample_ids=[sample.sample_id for sample in samples],
        )
