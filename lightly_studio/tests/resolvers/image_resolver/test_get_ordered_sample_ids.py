from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session

from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_ordered_sample_ids(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    other_collection_id = create_collection(session=db_session).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="/a.jpg", width=100),
            ImageStub(path="/b.jpg", width=800),
            ImageStub(path="/c.jpg", width=800),
            ImageStub(path="/d.jpg", width=800),
        ],
    )
    for image, day in [(images[1], 3), (images[2], 2), (images[3], 1)]:
        image.created_at = datetime(2024, 1, day, tzinfo=timezone.utc)
        db_session.add(image)
    db_session.commit()
    create_images(
        db_session=db_session,
        collection_id=other_collection_id,
        images=[ImageStub(path="/other.jpg", width=800)],
    )

    sample_ids = image_resolver.get_ordered_sample_ids(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(width=FilterDimensions(min=500)),
    )

    assert sample_ids == [images[3].sample_id, images[2].sample_id, images[1].sample_id]
