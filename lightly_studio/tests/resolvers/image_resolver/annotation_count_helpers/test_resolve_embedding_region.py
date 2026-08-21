from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.image import ImageTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import sample_embedding_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


def test_resolve_embedding_region__no_image_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)

    annotation_count_helpers.resolve_embedding_region(
        session=db_session,
        collection_id=collection.collection_id,
        image_filter=None,
    )


def test_resolve_embedding_region__no_sample_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    image_filter = ImageFilter()

    annotation_count_helpers.resolve_embedding_region(
        session=db_session,
        collection_id=collection.collection_id,
        image_filter=image_filter,
    )

    assert image_filter.sample_filter is None


def test_resolve_embedding_region__no_embedding_region(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    sample_filter = SampleFilter()
    image_filter = ImageFilter(sample_filter=sample_filter)

    annotation_count_helpers.resolve_embedding_region(
        session=db_session,
        collection_id=collection.collection_id,
        image_filter=image_filter,
    )

    assert sample_filter.region_sample_ids is None


def test_resolve_embedding_region__resolves_sample_ids(db_session: Session) -> None:
    collection_id, sample_ids = _setup_collection_with_coordinates(
        session=db_session,
        coordinates=[(1.0, 1.0), (5.0, 5.0), (100.0, 100.0)],
    )
    region = EmbeddingRegion(
        polygon=[
            Point2D(x=0, y=0),
            Point2D(x=10, y=0),
            Point2D(x=10, y=10),
            Point2D(x=0, y=10),
        ]
    )
    sample_filter = SampleFilter(embedding_region=region)
    image_filter = ImageFilter(sample_filter=sample_filter)

    annotation_count_helpers.resolve_embedding_region(
        session=db_session,
        collection_id=collection_id,
        image_filter=image_filter,
    )

    assert sample_filter.region_sample_ids is not None
    assert set(sample_filter.region_sample_ids) == {sample_ids[0], sample_ids[1]}


def _setup_collection_with_coordinates(
    session: Session,
    coordinates: list[tuple[float, float]],
) -> tuple[UUID, list[UUID]]:
    collection_id, embedding_model_id, images = _create_collection_with_embedded_samples(
        session=session,
        n_samples=len(coordinates),
    )
    _persist_two_dim_projection(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        images=images,
        coordinates=coordinates,
    )
    return collection_id, [image.sample_id for image in images]


def _create_collection_with_embedded_samples(
    session: Session,
    n_samples: int,
) -> tuple[UUID, UUID, list[ImageTable]]:
    collection = helpers_resolvers.create_collection(session=session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path=f"sample_{i}.png"), [float(i) + 0.1, 0.2, 0.3])
            for i in range(n_samples)
        ],
    )
    return collection.collection_id, embedding_model.embedding_model_id, images


def _persist_two_dim_projection(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    images: list[ImageTable],
    coordinates: list[tuple[float, float]],
) -> None:
    cache_key, sample_ids_ordered = sample_embedding_resolver.get_hash_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    coordinates_by_sample = {image.sample_id: coord for image, coord in zip(images, coordinates)}
    session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates_by_sample[sid][0] for sid in sample_ids_ordered],
            y=[coordinates_by_sample[sid][1] for sid in sample_ids_ordered],
        )
    )
    session.commit()
