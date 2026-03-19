"""Tests for FilterWithCollectionId."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers.filter_with_collection_id import FilterWithCollectionId
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_images,
)


def test_apply__combines_collection_scope_and_inner_filter(db_session: Session) -> None:
    col_a = create_collection(session=db_session, collection_name="col_a")
    col_b = create_collection(session=db_session, collection_name="col_b")

    images = create_images(
        db_session=db_session,
        collection_id=col_a.collection_id,
        images=[
            ImageStub(path="a_small.png", width=100),
            ImageStub(path="a_large.png", width=2000),
        ],
    )
    create_images(
        db_session=db_session,
        collection_id=col_b.collection_id,
        images=[ImageStub(path="b_small.png", width=100)],
    )

    query = select(ImageTable).join(ImageTable.sample)
    filtered = FilterWithCollectionId[ImageFilter](
        collection_id=col_a.collection_id,
        filter=ImageFilter(width=FilterDimensions(min=500)),
    ).apply(query)
    result = db_session.exec(filtered).all()

    assert len(result) == 1
    assert images[1].sample_id == result[0].sample_id
    assert images[1].width == result[0].width


def test_apply__returns_empty_for_wrong_collection(db_session: Session) -> None:

    query = select(ImageTable).join(ImageTable.sample)
    filtered = FilterWithCollectionId[ImageFilter](
        collection_id=uuid4(),
        filter=ImageFilter(),
    ).apply(query)
    result = [row.sample_id for row in db_session.exec(filtered).all()]

    assert result == []
