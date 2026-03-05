from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_collection_id_by_group_id(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component sample
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id}],
    )[0]

    # Call get_collection_id_by_group
    collection_id = group_resolver.get_collection_id_by_group_id(
        session=db_session, group_id=group_id
    )

    # Verify the collection_id matches the group collection
    assert collection_id is not None
    assert collection_id == group_col.collection_id


def test_get_collection_id_by_group_id__non_existent_group(db_session: Session) -> None:
    # Call get_collection_id_by_group with a non-existent group ID
    non_existent_id = uuid4()
    collection_id = group_resolver.get_collection_id_by_group_id(
        session=db_session, group_id=non_existent_id
    )

    # Verify it returns None
    assert collection_id is None


def test_get_collection_id_by_group_id__multiple_groups(db_session: Session) -> None:
    # Create two group collections
    group_col_1 = create_collection(session=db_session, sample_type=SampleType.GROUP)
    group_col_2 = create_collection(session=db_session, sample_type=SampleType.GROUP)

    components_1 = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col_1.collection_id,
        components=[("front", SampleType.IMAGE)],
    )
    components_2 = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col_2.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_image_1 = create_images(
        db_session=db_session,
        collection_id=components_1["front"].collection_id,
        images=[ImageStub(path="front_1.jpg")],
    )[0]
    front_image_2 = create_images(
        db_session=db_session,
        collection_id=components_2["front"].collection_id,
        images=[ImageStub(path="front_2.jpg")],
    )[0]

    # Create groups in different collections
    group_id_1 = group_resolver.create_many(
        session=db_session,
        collection_id=group_col_1.collection_id,
        groups=[{front_image_1.sample_id}],
    )[0]
    group_id_2 = group_resolver.create_many(
        session=db_session,
        collection_id=group_col_2.collection_id,
        groups=[{front_image_2.sample_id}],
    )[0]

    # Call get_collection_id_by_group for both groups
    collection_id_1 = group_resolver.get_collection_id_by_group_id(
        session=db_session, group_id=group_id_1
    )
    collection_id_2 = group_resolver.get_collection_id_by_group_id(
        session=db_session, group_id=group_id_2
    )

    # Verify each returns the correct collection_id
    assert collection_id_1 == group_col_1.collection_id
    assert collection_id_2 == group_col_2.collection_id
    assert collection_id_1 != collection_id_2
