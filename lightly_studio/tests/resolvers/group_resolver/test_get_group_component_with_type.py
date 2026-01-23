import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_group_component_with_type(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("img", SampleType.IMAGE), ("vid", SampleType.VIDEO)],
    )

    # Create component samples
    image = create_image(
        session=db_session,
        collection_id=components["img"].collection_id,
    )
    video = create_video(
        session=db_session,
        collection_id=components["vid"].collection_id,
        video=VideoStub(),
    )

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{image.sample_id, video.sample_id}],
    )[0]

    # Call get_group_component_with_type
    img_comp = group_resolver.get_group_component_with_type(
        session=db_session, sample_id=group_id, key="img"
    )
    vid_comp = group_resolver.get_group_component_with_type(
        session=db_session, sample_id=group_id, key="vid"
    )
    assert img_comp == (image.sample_id, SampleType.IMAGE)
    assert vid_comp == (video.sample_id, SampleType.VIDEO)

    # Non-existing key
    with pytest.raises(KeyError):
        group_resolver.get_group_component_with_type(
            session=db_session, sample_id=group_id, key="non_existing"
        )


def test_get_group_component_with_type__unset_component(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("img", SampleType.IMAGE)],
    )

    # Create a group with no components
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[set()],
    )[0]

    # Call get_group_component_with_type
    comp = group_resolver.get_group_component_with_type(
        session=db_session, sample_id=group_id, key="img"
    )
    assert comp == (None, SampleType.IMAGE)
