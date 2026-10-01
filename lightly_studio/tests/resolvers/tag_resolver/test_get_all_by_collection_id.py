from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_read_tags(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    tag_1 = create_tag(session=db_session, collection_id=collection_id, tag_name="tag_1")
    create_tag(session=db_session, collection_id=collection_id, tag_name="tag_2")
    create_tag(session=db_session, collection_id=collection_id, tag_name="tag_3")

    # get all tags of a collection
    tags = tag_resolver.get_all_by_collection_id(session=db_session, collection_id=collection_id)
    assert len(tags) == 3
    # check order
    tag = tags[0]
    assert tag.tag_id == tag_1.tag_id
    assert tag.name == tag_1.name


def test_read_tags__paginated(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    total = 10
    chunk_size = total // 2
    for i in range(total):
        create_tag(session=db_session, collection_id=collection_id, tag_name=f"example_tag_{i}")

    # get first chunk/page
    page_1 = tag_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        offset=0,
        limit=chunk_size,
    )
    assert len(page_1) == chunk_size

    # get second chunk/page
    page_2 = tag_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        offset=5,
        limit=chunk_size,
    )
    assert len(page_2) == chunk_size

    # assert that the two chunks are different
    assert page_1 != page_2
    assert page_1[0].name != page_2[0].name
