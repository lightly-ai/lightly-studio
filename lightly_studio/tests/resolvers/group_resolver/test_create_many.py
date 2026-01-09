from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_create_many(db_session: Session) -> None:
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples
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

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[
            {front_images[0].sample_id, back_images[0].sample_id},
            {front_images[1].sample_id, back_images[1].sample_id},
        ],
    )
    assert len(group_ids) == 2

    # TODO(Michal, 01/2026): Assert created groups once we have a way to fetch them.
