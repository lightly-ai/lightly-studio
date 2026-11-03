from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_remove_samples_from_tag_from_query(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"s{i}.png")
        for i in range(3)
    ]
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[i.sample_id for i in images]
    )
    query = select(SampleTable.sample_id).where(
        col(SampleTable.sample_id).in_([images[0].sample_id, images[1].sample_id])
    )

    tag_resolver.remove_samples_from_tag_from_query(
        session=db_session, tag_id=tag.tag_id, sample_ids_query=query
    )

    remaining = tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)
    assert set(remaining) == {images[2].sample_id}
