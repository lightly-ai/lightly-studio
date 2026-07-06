"""Tests for the embedding-region resolver (server-side point-in-polygon)."""

from __future__ import annotations

from uuid import UUID

import numpy as np
from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import embedding_region_resolver, sample_embedding_resolver
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


def test_get_sample_ids_in_region(db_session: Session) -> None:
    collection_id, sample_ids = _setup_collection_with_coordinates(
        session=db_session,
        coordinates=[(1.0, 1.0), (5.0, 5.0), (100.0, 100.0)],
    )

    selected = embedding_region_resolver.get_sample_ids_in_region(
        session=db_session,
        collection_id=collection_id,
        region=_square(x_min=0, y_min=0, x_max=10, y_max=10),
    )

    assert set(selected) == {sample_ids[0], sample_ids[1]}


def test_get_sample_ids_in_region__empty_region(db_session: Session) -> None:
    collection_id, _ = _setup_collection_with_coordinates(
        session=db_session,
        coordinates=[(1.0, 1.0), (5.0, 5.0)],
    )

    selected = embedding_region_resolver.get_sample_ids_in_region(
        session=db_session,
        collection_id=collection_id,
        region=_square(x_min=50, y_min=50, x_max=60, y_max=60),
    )

    assert selected == []


def test_get_sample_ids_in_region__no_embedding_model(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)

    selected = embedding_region_resolver.get_sample_ids_in_region(
        session=db_session,
        collection_id=collection.collection_id,
        region=_square(x_min=0, y_min=0, x_max=10, y_max=10),
    )

    assert selected == []


def test_points_in_polygon() -> None:
    region = _square(x_min=0, y_min=0, x_max=10, y_max=10)
    x = np.array([5, 15, -1, 9.9, 5], dtype=np.float32)
    y = np.array([5, 5, 5, 9.9, 20], dtype=np.float32)

    mask = embedding_region_resolver._points_in_polygon(x=x, y=y, region=region)

    assert mask.tolist() == [True, False, False, True, False]


def test_points_in_polygon__concave() -> None:
    # An arrow-shaped concave polygon with a notch at the top center.
    region = EmbeddingRegion(
        polygon=[
            Point2D(x=0, y=0),
            Point2D(x=10, y=0),
            Point2D(x=10, y=10),
            Point2D(x=5, y=4),
            Point2D(x=0, y=10),
        ]
    )
    # (5, 8) sits in the notch (outside); (5, 2) is well inside.
    x = np.array([5, 5, 1], dtype=np.float32)
    y = np.array([8, 2, 1], dtype=np.float32)

    mask = embedding_region_resolver._points_in_polygon(x=x, y=y, region=region)

    assert mask.tolist() == [False, True, True]


def _square(x_min: float, y_min: float, x_max: float, y_max: float) -> EmbeddingRegion:
    return EmbeddingRegion(
        polygon=[
            Point2D(x=x_min, y=y_min),
            Point2D(x=x_max, y=y_min),
            Point2D(x=x_max, y=y_max),
            Point2D(x=x_min, y=y_max),
        ]
    )


def _seed_2d_coordinates(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    coordinates: dict[UUID, tuple[float, float]],
) -> list[UUID]:
    """Seed the cached 2D projection with deterministic coordinates.

    Returns the ordered sample ids as ``get_twodim_embeddings`` would return them.
    """
    cache_key, sample_ids = sample_embedding_resolver.get_hash_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates[sample_id][0] for sample_id in sample_ids],
            y=[coordinates[sample_id][1] for sample_id in sample_ids],
        )
    )
    session.commit()
    return sample_ids


def _setup_collection_with_coordinates(
    session: Session,
    coordinates: list[tuple[float, float]],
) -> tuple[UUID, list[UUID]]:
    collection = helpers_resolvers.create_collection(session=session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        # Distinct first dimensions keep the deterministic cache key stable across samples.
        images_and_embeddings=[
            (ImageStub(path=f"sample_{index}.png"), [float(index) + 0.1, 0.2, 0.3])
            for index in range(len(coordinates))
        ],
    )
    coordinates_by_sample = {
        image.sample_id: coordinate for image, coordinate in zip(images, coordinates)
    }
    _seed_2d_coordinates(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        coordinates=coordinates_by_sample,
    )
    # Return sample ids in the same order as ``coordinates`` so callers can index by
    # coordinate. ``_seed_2d_coordinates`` seeds by sample id, so its own (hash-ordered)
    # return value need not match the coordinate order.
    return collection.collection_id, [image.sample_id for image in images]
