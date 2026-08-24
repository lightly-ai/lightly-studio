from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.image import ImageTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import collection_resolver, sample_embedding_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_image,
    create_samples_with_embeddings,
)


def test_export__no_filter__returns_all_samples(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )

    result = collection_resolver.export(session=db_session, collection_id=collection_id)

    assert sorted(result) == sorted([image_a.file_path_abs, image_b.file_path_abs])


def test_export__collection_filter__returns_matching_samples(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/c.png")

    collection_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=[image_a.sample_id, image_b.sample_id])
    )
    result = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        collection_filter=collection_filter,
    )

    assert sorted(result) == sorted([image_a.file_path_abs, image_b.file_path_abs])


def test_get_filtered_samples_count__no_filter__returns_total(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/a.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/b.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/c.png")

    count = collection_resolver.get_filtered_samples_count(
        session=db_session, collection_id=collection_id
    )

    assert count == 3


def test_get_filtered_samples_count__collection_filter__returns_matching_count(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/b.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/path/c.png")

    collection_filter = ImageFilter(sample_filter=SampleFilter(sample_ids=[image_a.sample_id]))
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=collection_id,
        collection_filter=collection_filter,
    )

    assert count == 1


def _setup_embedding_region(
    db_session: Session,
) -> tuple[ImageTable, ImageTable, ImageTable, EmbeddingRegion]:
    """Create three samples with 2D embeddings; a and b inside the region, c outside."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    image_a, image_b, image_c = create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="sample_a.png"), [0.1, 0.2, 0.3]),
            (ImageStub(path="sample_b.png"), [1.1, 0.2, 0.3]),
            (ImageStub(path="sample_c.png"), [2.1, 0.2, 0.3]),
        ],
    )
    cache_key, ordered_sample_ids = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    coordinates = {
        image_a.sample_id: (1.0, 1.0),
        image_b.sample_id: (5.0, 5.0),
        image_c.sample_id: (100.0, 100.0),
    }
    db_session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates[sid][0] for sid in ordered_sample_ids],
            y=[coordinates[sid][1] for sid in ordered_sample_ids],
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
    return image_a, image_b, image_c, region


def test_export__embedding_region_filter__returns_samples_inside_region(
    db_session: Session,
) -> None:
    image_a, image_b, _image_c, region = _setup_embedding_region(db_session)
    collection_id = image_a.sample.collection_id

    result = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        collection_filter=ImageFilter(sample_filter=SampleFilter(embedding_region=region)),
    )

    assert sorted(result) == sorted([image_a.file_path_abs, image_b.file_path_abs])


def test_get_filtered_samples_count__embedding_region_filter__returns_count_inside_region(
    db_session: Session,
) -> None:
    image_a, _image_b, _image_c, region = _setup_embedding_region(db_session)
    collection_id = image_a.sample.collection_id

    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=collection_id,
        collection_filter=ImageFilter(sample_filter=SampleFilter(embedding_region=region)),
    )

    assert count == 2
