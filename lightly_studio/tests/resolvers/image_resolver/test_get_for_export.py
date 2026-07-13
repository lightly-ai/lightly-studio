from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import image_resolver, sample_embedding_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_samples_with_embeddings,
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

    created_images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="/data/small.jpg", width=100, height=100),
            ImageStub(path="/data/large.jpg", width=800, height=800),
        ],
    )
    small_image = created_images[0]
    large_image = created_images[1]

    result = list(
        image_resolver.get_for_export(
            session=db_session,
            collection_id=collection.collection_id,
            collection_filter=ImageFilter(width=FilterDimensions(min=500)),
        )
    )

    assert {s.sample_id for s in result} == {large_image.sample_id}
    assert small_image.sample_id not in {s.sample_id for s in result}


def test_get_for_export__with_embedding_region_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    images = create_samples_with_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="inside1.jpg"), [1.0, 0.2, 0.3]),
            (ImageStub(path="inside2.jpg"), [2.0, 0.2, 0.3]),
            (ImageStub(path="outside.jpg"), [3.0, 0.2, 0.3]),
        ],
    )
    image_inside1 = images[0]
    image_inside2 = images[1]
    image_outside = images[2]

    # Seed 2D coordinates: inside1 and inside2 within (0,0)-(10,10), outside at (100, 100).
    cache_key, sample_ids_in_order = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    coordinates_by_id = {
        image_inside1.sample_id: (1.0, 1.0),
        image_inside2.sample_id: (5.0, 5.0),
        image_outside.sample_id: (100.0, 100.0),
    }
    db_session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates_by_id[sid][0] for sid in sample_ids_in_order],
            y=[coordinates_by_id[sid][1] for sid in sample_ids_in_order],
        )
    )
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
    assert image_outside.sample_id not in {s.sample_id for s in result}
