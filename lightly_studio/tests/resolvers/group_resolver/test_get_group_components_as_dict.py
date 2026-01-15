from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_group_components_as_dict(db_session: Session) -> None:
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
        images=[ImageStub()],
    )[0]

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id}],
    )[0]

    # Call get_group_components_as_dict
    comps = group_resolver.get_group_components_as_dict(session=db_session, sample_id=group_id)

    assert comps["front"] is not None
    assert comps["front"].sample_id == front_image.sample_id
    assert comps["back"] is None


def test_get_group_components_as_dict__all_none(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create a group with no components
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[set()],
    )[0]

    # Call get_group_components_as_dict
    comps = group_resolver.get_group_components_as_dict(session=db_session, sample_id=group_id)
    assert comps["front"] is None
    assert comps["back"] is None
