import uuid

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_group_components_by_group_id(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]
    back_image = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_0.jpg")],
    )[0]

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id, back_image.sample_id}],
    )[0]

    # Call get_group_samples
    samples = group_resolver.get_group_components_by_group_id(session=db_session, group_id=group_id)

    # Verify results
    assert len(samples) == 2
    sample_ids = {sample.sample_id for sample in samples}
    assert front_image.sample_id in sample_ids
    assert back_image.sample_id in sample_ids


def test_get_group_components_by_group_id__partial_group(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples (only front)
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]

    # Create a partial group (only has front component)
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id}],
    )[0]

    # Call get_group_samples
    samples = group_resolver.get_group_components_by_group_id(session=db_session, group_id=group_id)

    # Verify results
    assert len(samples) == 1
    assert samples[0].sample_id == front_image.sample_id


def test_get_group_components_by_group_id__empty_result(db_session: Session) -> None:
    # Call get_group_samples with a non-existent group ID (using a random UUID)
    # This should return empty list as the group does not exist
    samples = group_resolver.get_group_components_by_group_id(
        session=db_session, group_id=uuid.uuid4()
    )

    # Verify results - should be empty
    assert len(samples) == 0


def test_get_group_components_by_group_id__multiple_groups(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples for first group
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg"), ImageStub(path="front_1.jpg")],
    )
    back_images = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_0.jpg"), ImageStub(path="back_1.jpg")],
    )

    # Create two groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[
            {front_images[0].sample_id, back_images[0].sample_id},
            {front_images[1].sample_id, back_images[1].sample_id},
        ],
    )

    # Test first group
    samples_0 = group_resolver.get_group_components_by_group_id(
        session=db_session, group_id=group_ids[0]
    )
    assert len(samples_0) == 2
    sample_ids_0 = {sample.sample_id for sample in samples_0}
    assert front_images[0].sample_id in sample_ids_0
    assert back_images[0].sample_id in sample_ids_0

    # Test second group
    samples_1 = group_resolver.get_group_components_by_group_id(
        session=db_session, group_id=group_ids[1]
    )
    assert len(samples_1) == 2
    sample_ids_1 = {sample.sample_id for sample in samples_1}
    assert front_images[1].sample_id in sample_ids_1
    assert back_images[1].sample_id in sample_ids_1

    # Ensure no overlap between groups
    assert sample_ids_0.isdisjoint(sample_ids_1)
