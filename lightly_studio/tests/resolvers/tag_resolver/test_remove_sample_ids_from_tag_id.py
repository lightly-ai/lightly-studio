from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_tag


def test_remove_sample_ids_from_tag_id__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More sample ids than PostgreSQL's 65,535-parameter cap.
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="t")
    sample_ids = [uuid4() for _ in range(70_000)]

    result = tag_resolver.remove_sample_ids_from_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=sample_ids
    )

    assert result is not None
