import uuid

from sqlmodel import Session

from lightly_studio.resolvers import (
    image_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


def test_get_many_by_id(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    # Create samples.
    image1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    # Act.
    samples = image_resolver.get_many_by_id(
        session=db_session, sample_ids=[image1.sample_id, image2.sample_id]
    )

    # Assert.
    assert len(samples) == 2
    assert samples[0].file_name == "sample1.png"
    assert samples[1].file_name == "sample2.png"


def test_get_many_by_id__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More ids than PostgreSQL's 65,535-parameter cap; the chunked query must not raise.
    sample_ids = [uuid.uuid4() for _ in range(70_000)]
    assert image_resolver.get_many_by_id(session=db_session, sample_ids=sample_ids) == []
