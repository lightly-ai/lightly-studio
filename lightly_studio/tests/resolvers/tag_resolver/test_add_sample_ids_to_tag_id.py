from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_add_and_remove_sample_ids_to_tag_id(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag_1 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag_all",
        kind="sample",
    )
    tag_2 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag_odd",
        kind="sample",
    )

    total_samples = 10
    images = []
    for i in range(total_samples):
        image = create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"sample{i}.png",
        )
        images.append(image)

    # add samples to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # add every odd samples to tag_2
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
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
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[s.sample_id for i, s in enumerate(images) if i % 2 == 0],
    )

    assert len(tag_1.samples) == total_samples / 2
    assert len(tag_2.samples) == total_samples / 2

    tag_1_samples_sorted = sorted(tag_1.samples, key=lambda s: s.sample_id)
    tag_2_samples_sorted = sorted(tag_2.samples, key=lambda s: s.sample_id)
    assert tag_1_samples_sorted == tag_2_samples_sorted


def test_add_and_remove_sample_ids_to_tag_id__twice_same_sample_ids(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag_1 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag_all",
        kind="sample",
    )

    total_samples = 10
    images = []
    for i in range(total_samples):
        image = create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"sample{i}.png",
        )
        images.append(image)

    # add samples to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # adding the same samples to tag_1 does not create an error
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # ensure all samples were added once
    assert len(tag_1.samples) == total_samples

    # remove samples from
    tag_resolver.remove_sample_ids_from_tag_id(
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )
    # removing the same samples to tag_1 does not create an error
    tag_resolver.remove_sample_ids_from_tag_id(
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in images],
    )

    # ensure all samples were removed again
    assert len(tag_1.samples) == 0
