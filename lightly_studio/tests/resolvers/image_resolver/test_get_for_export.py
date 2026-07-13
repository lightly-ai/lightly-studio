from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import image_resolver, sample_embedding_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_get_for_export__no_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)

    image1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/data/img1.jpg",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/data/img2.jpg",
    )
    create_image(
        session=db_session,
        collection_id=other_collection.collection_id,
        file_path_abs="/data/other.jpg",
    )

    result = list(
        image_resolver.get_for_export(
            session=db_session,
            collection_id=collection.collection_id,
            collection_filter=None,
        )
    )

    assert {s.sample_id for s in result} == {image1.sample_id, image2.sample_id}


def test_get_for_export__with_image_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    small_image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/data/small.jpg",
        width=100,
        height=100,
    )
    large_image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/data/large.jpg",
        width=800,
        height=800,
    )

    result = list(
        image_resolver.get_for_export(
            session=db_session,
            collection_id=collection.collection_id,
            collection_filter=ImageFilter(width=FilterDimensions(min=500)),
        )
    )

    assert {s.sample_id for s in result} == {large_image.sample_id}


def test_get_for_export__with_embedding_region_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    image_inside1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="inside1.jpg",
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_inside1.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 0.2, 0.3],
    )
    image_inside2 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="inside2.jpg",
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_inside2.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[2.0, 0.2, 0.3],
    )
    image_outside = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="outside.jpg",
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_outside.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[3.0, 0.2, 0.3],
    )

    # Seed 2D coordinates: inside1 and inside2 within (0,0)-(10,10), outside at (100, 100).
    cache_key, sample_ids_in_order = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    inside1_i = sample_ids_in_order.index(image_inside1.sample_id)
    inside2_i = sample_ids_in_order.index(image_inside2.sample_id)
    outside_i = sample_ids_in_order.index(image_outside.sample_id)
    x = [0.0, 0.0, 0.0]
    y = [0.0, 0.0, 0.0]
    x[inside1_i] = 1.0
    y[inside1_i] = 1.0
    x[inside2_i] = 5.0
    y[inside2_i] = 5.0
    x[outside_i] = 100.0
    y[outside_i] = 100.0
    db_session.add(TwoDimEmbeddingTable(hash=cache_key, x=x, y=y))
    db_session.commit()

    region = EmbeddingRegion(
        polygon=[
            Point2D(x=0, y=0),
            Point2D(x=10, y=0),
            Point2D(x=10, y=10),
            Point2D(x=0, y=10),
        ]
    )
    collection_filter = ImageFilter(sample_filter=SampleFilter(embedding_region=region))

    result = list(
        image_resolver.get_for_export(
            session=db_session,
            collection_id=collection.collection_id,
            collection_filter=collection_filter,
        )
    )

    assert {s.sample_id for s in result} == {image_inside1.sample_id, image_inside2.sample_id}
