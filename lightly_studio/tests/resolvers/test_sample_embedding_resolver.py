from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
)
from lightly_studio.resolvers import image_resolver_legacy, sample_embedding_resolver
from tests.helpers_resolvers import (
    create_dataset,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_create_sample_embedding(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    image = create_image(session=test_db, dataset_id=dataset_id)
    sample_id = image.sample_id
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
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
    # Create a dataset
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create 3 samples.
    samples = [
        create_image(
            session=test_db, dataset_id=dataset_id, file_path_abs=f"/path/to/sample_{i}.png"
        )
        for i in range(3)
    ]
    # Create an embedding model
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
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
        sample_from_db = image_resolver_legacy.get_by_id(
            session=test_db, dataset_id=dataset_id, sample_id=sample.sample_id
        )
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
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    image = create_image(session=test_db, dataset_id=dataset_id)
    sample_id = image.sample_id
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
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
    sample_from_db = image_resolver_legacy.get_by_id(
        session=test_db, dataset_id=dataset_id, sample_id=sample_id
    )
    assert sample_from_db is not None
    assert len(sample_from_db.sample.embeddings) == 1
    assert sample_embedding.embedding == sample_from_db.sample.embeddings[0].embedding


def test_get_sample_embeddings_by_sample_ids(test_db: Session) -> None:
    # Create a dataset
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create 3 samples.
    samples = [
        create_image(
            session=test_db, dataset_id=dataset_id, file_path_abs=f"/path/to/sample_{i}.png"
        )
        for i in range(3)
    ]
    # Create an embedding model
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
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
    all_in_dataset = sample_embedding_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_id=embedding_model_id,
    )
    assert len(all_in_dataset) == 3
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
