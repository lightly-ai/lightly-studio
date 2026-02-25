from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_sample_ids(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.IMAGE)
    other_collection = create_collection(session=test_db, sample_type=SampleType.IMAGE)

    created_images = create_images(
        db_session=test_db,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="/path/to/small.jpg", width=100, height=100),
            ImageStub(path="/path/to/large.jpg", width=800, height=800),
        ],
    )
    create_images(
        db_session=test_db,
        collection_id=other_collection.collection_id,
        images=[ImageStub(path="/path/to/other.jpg", width=800, height=800)],
    )

    all_sample_ids = image_resolver.get_sample_ids(
        session=test_db,
        filters=ImageFilter(sample_filter=SampleFilter(collection_id=collection.collection_id)),
    )
    assert all_sample_ids == {img.sample_id for img in created_images}

    filtered_sample_ids = image_resolver.get_sample_ids(
        session=test_db,
        filters=ImageFilter(
            sample_filter=SampleFilter(collection_id=collection.collection_id),
            width=FilterDimensions(min=500),
        ),
    )
    assert filtered_sample_ids == {created_images[1].sample_id}


def test_get_sample_ids__no_collection_id(test_db: Session) -> None:
    with pytest.raises(ValueError, match="Collection ID must be provided in the sample filter."):
        image_resolver.get_sample_ids(
            session=test_db,
            filters=ImageFilter(width=FilterDimensions(min=500)),
        )
