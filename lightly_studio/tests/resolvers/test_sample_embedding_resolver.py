from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
)
from lightly_studio.resolvers import image_resolver, sample_embedding_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
)


def test_create_sample_embedding(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    image = create_image(session=test_db, collection_id=collection_id)
    sample_id = image.sample_id
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    sample_embedding = create_sample_embedding(
        session=test_db,
        sample_id=sample_id,
        embedding=[1.0, 2.0, 3.0],
        embedding_model_id=embedding_model_id,
    )
    assert sample_embedding.sample_id == sample_id
    assert sample_embedding.embedding == [1.0, 2.0, 3.0]


def test_create_many_sample_embeddings(test_db: Session) -> None:
    # Create a collection
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    # Create 3 samples.
    samples = [
        create_image(
            session=test_db, collection_id=collection_id, file_path_abs=f"/path/to/sample_{i}.png"
        )
        for i in range(3)
    ]
    # Create an embedding model
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="batch_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id

    # Create embedding inputs for batch creation.
    embedding_inputs = [
        SampleEmbeddingCreate(
            sample_id=sample.sample_id,
            embedding_model_id=embedding_model_id,
            embedding=[float(i), float(i + 1), float(i + 2)],
        )
        for i, sample in enumerate(samples)
    ]

    # Create many embeddings in a batch.
    sample_embedding_resolver.create_many(session=test_db, sample_embeddings=embedding_inputs)

    # Verify all embeddings were created correctly.
    for i, sample in enumerate(samples):
        sample_from_db = image_resolver.get_by_id(session=test_db, sample_id=sample.sample_id)
        assert sample_from_db is not None
        assert len(sample_from_db.sample.embeddings) == 1
        assert sample_from_db.sample.embeddings[0].embedding == [
            float(i),
            float(i + 1),
            float(i + 2),
        ]


def test_add_sample_embedding_to_sample(test_db: Session) -> None:
    # This test checks if the relationship between a sample and its embeddings
    # is correctly set up and we can read embedding out of the sample after it
    # is created.
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    image = create_image(session=test_db, collection_id=collection_id)
    sample_id = image.sample_id
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    sample_embedding = create_sample_embedding(
        session=test_db,
        sample_id=sample_id,
        embedding=[1.0, 2.0, 3.0],
        embedding_model_id=embedding_model_id,
    )
    assert sample_embedding.sample_id == sample_id
    assert sample_embedding.embedding == [1.0, 2.0, 3.0]

    assert len(image.sample.embeddings) == 1
    assert sample_embedding.embedding == image.sample.embeddings[0].embedding

    # Read sample from the db and check the embedding.
    sample_from_db = image_resolver.get_by_id(session=test_db, sample_id=sample_id)
    assert sample_from_db is not None
    assert len(sample_from_db.sample.embeddings) == 1
    assert sample_embedding.embedding == sample_from_db.sample.embeddings[0].embedding


def test_get_sample_embeddings_by_sample_ids(test_db: Session) -> None:
    # Create a collection
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    # Create 3 samples.
    samples = [
        create_image(
            session=test_db, collection_id=collection_id, file_path_abs=f"/path/to/sample_{i}.png"
        )
        for i in range(3)
    ]
    # Create an embedding model
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="batch_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id

    # Create embedding inputs for batch creation.
    embedding_inputs = [
        SampleEmbeddingCreate(
            sample_id=sample.sample_id,
            embedding_model_id=embedding_model_id,
            embedding=[float(i), float(i + 1), float(i + 2)],
        )
        for i, sample in enumerate(samples)
    ]

    # Create many embeddings in a batch.
    sample_embedding_resolver.create_many(session=test_db, sample_embeddings=embedding_inputs)
    all_in_collection = sample_embedding_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    assert len(all_in_collection) == 3
    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=test_db,
        sample_ids=[samples[0].sample_id],
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings) == 1
    assert embeddings[0].sample_id == samples[0].sample_id
    assert embeddings[0].embedding == samples[0].sample.embeddings[0].embedding

    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=test_db,
        sample_ids=[samples[0].sample_id],
        embedding_model_id=uuid4(),
    )
    assert len(embeddings) == 0

    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=test_db,
        sample_ids=[uuid4()],
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings) == 0


def test_get_embedding_count(test_db: Session) -> None:
    # Create collections
    col1_id = create_collection(session=test_db).collection_id
    col2_id = create_collection(session=test_db, collection_name="col2").collection_id

    # Create samples.
    images_col1 = create_images(
        db_session=test_db,
        collection_id=col1_id,
        images=[ImageStub("sample1.png"), ImageStub("sample2.png"), ImageStub("sample3.png")],
    )
    create_images(db_session=test_db, collection_id=col2_id, images=[ImageStub("sample.png")])

    # Create an embedding models
    embedding_model_1 = create_embedding_model(session=test_db, collection_id=col1_id)
    embedding_model_1_id = embedding_model_1.embedding_model_id
    embedding_model_2 = create_embedding_model(session=test_db, collection_id=col1_id)
    embedding_model_2_id = embedding_model_2.embedding_model_id

    # Create embeddings for col1
    embedding_inputs = [
        SampleEmbeddingCreate(
            sample_id=images_col1[0].sample_id,
            embedding_model_id=embedding_model_1_id,
            embedding=[0.0, 0.0, 0.0],
        ),
        SampleEmbeddingCreate(
            sample_id=images_col1[1].sample_id,
            embedding_model_id=embedding_model_1_id,
            embedding=[0.0, 0.0, 0.0],
        ),
    ]
    sample_embedding_resolver.create_many(session=test_db, sample_embeddings=embedding_inputs)

    # Collection 1 has two embeddings
    count = sample_embedding_resolver.get_embedding_count(
        session=test_db,
        collection_id=col1_id,
        embedding_model_id=embedding_model_1_id,
    )
    assert count == 2

    # Collection 2 has no embeddings
    count = sample_embedding_resolver.get_embedding_count(
        session=test_db,
        collection_id=col2_id,
        embedding_model_id=embedding_model_2_id,
    )
    assert count == 0
