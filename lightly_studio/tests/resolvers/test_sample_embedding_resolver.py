from __future__ import annotations

from uuid import uuid4

import numpy as np
from sqlmodel import Session

from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
)
from lightly_studio.resolvers import image_resolver, sample_embedding_resolver, tag_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
    create_tag,
)


def test_create_sample_embedding(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    sample_id = image.sample_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    sample_embedding = create_sample_embedding(
        session=db_session,
        sample_id=sample_id,
        embedding=[1.0, 2.0, 3.0],
        embedding_model_id=embedding_model_id,
    )
    assert sample_embedding.sample_id == sample_id
    assert list(sample_embedding.embedding) == [1.0, 2.0, 3.0]


def test_create_many_sample_embeddings(db_session: Session) -> None:
    # Create a collection
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create 3 samples.
    samples = [
        create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample_{i}.png",
        )
        for i in range(3)
    ]
    # Create an embedding model
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="batch_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id

    # Create embedding inputs for batch creation.
    embedding_inputs = [
        SampleEmbeddingCreate(
            sample_id=sample.sample_id,
            embedding_model_id=embedding_model_id,
            embedding=np.array([float(i), float(i + 1), float(i + 2)], dtype=np.float32),
        )
        for i, sample in enumerate(samples)
    ]

    # Create many embeddings in a batch.
    sample_embedding_resolver.create_many(session=db_session, sample_embeddings=embedding_inputs)

    # Verify all embeddings were created correctly.
    for i, sample in enumerate(samples):
        sample_from_db = image_resolver.get_by_id(session=db_session, sample_id=sample.sample_id)
        assert sample_from_db is not None
        assert len(sample_from_db.sample.embeddings) == 1
        assert list(sample_from_db.sample.embeddings[0].embedding) == [
            float(i),
            float(i + 1),
            float(i + 2),
        ]


def test_add_sample_embedding_to_sample(db_session: Session) -> None:
    # This test checks if the relationship between a sample and its embeddings
    # is correctly set up and we can read embedding out of the sample after it
    # is created.
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    sample_id = image.sample_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    sample_embedding = create_sample_embedding(
        session=db_session,
        sample_id=sample_id,
        embedding=[1.0, 2.0, 3.0],
        embedding_model_id=embedding_model_id,
    )
    assert sample_embedding.sample_id == sample_id
    assert list(sample_embedding.embedding) == [1.0, 2.0, 3.0]

    assert len(image.sample.embeddings) == 1
    assert list(sample_embedding.embedding) == list(image.sample.embeddings[0].embedding)

    # Read sample from the db and check the embedding.
    sample_from_db = image_resolver.get_by_id(session=db_session, sample_id=sample_id)
    assert sample_from_db is not None
    assert len(sample_from_db.sample.embeddings) == 1
    assert list(sample_embedding.embedding) == list(sample_from_db.sample.embeddings[0].embedding)


def test_get_sample_embeddings_by_sample_ids(db_session: Session) -> None:
    # Create a collection
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create 3 samples.
    samples = [
        create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample_{i}.png",
        )
        for i in range(3)
    ]
    # Create an embedding model
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="batch_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id

    # Create embedding inputs for batch creation.
    embedding_inputs = [
        SampleEmbeddingCreate(
            sample_id=sample.sample_id,
            embedding_model_id=embedding_model_id,
            embedding=np.array([float(i), float(i + 1), float(i + 2)], dtype=np.float32),
        )
        for i, sample in enumerate(samples)
    ]

    # Create many embeddings in a batch.
    sample_embedding_resolver.create_many(session=db_session, sample_embeddings=embedding_inputs)
    embeddings_by_collection = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings_by_collection) == 3
    embeddings_by_id = sample_embedding_resolver.get_by_sample_ids(
        session=db_session,
        sample_ids=[row.sample_id for row in embeddings_by_collection],
        embedding_model_id=embedding_model_id,
    )
    assert {row.sample_id: list(row.embedding) for row in embeddings_by_collection} == {
        row.sample_id: list(row.embedding) for row in embeddings_by_id
    }
    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=db_session,
        sample_ids=[samples[0].sample_id],
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings) == 1
    assert embeddings[0].sample_id == samples[0].sample_id
    assert list(embeddings[0].embedding) == list(samples[0].sample.embeddings[0].embedding)

    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=db_session,
        sample_ids=[samples[0].sample_id],
        embedding_model_id=uuid4(),
    )
    assert len(embeddings) == 0

    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=db_session,
        sample_ids=[uuid4()],
        embedding_model_id=embedding_model_id,
    )
    assert len(embeddings) == 0


def test_get_all_by_collection_id_with_filter(db_session: Session) -> None:
    # Create a collection with 3 samples and their embeddings.
    collection_id = create_collection(session=db_session).collection_id
    samples = [
        create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/path/{i}.png"
        )
        for i in range(3)
    ]
    embedding_model_id = create_embedding_model(
        session=db_session, collection_id=collection_id
    ).embedding_model_id
    sample_embedding_resolver.create_many(
        session=db_session,
        sample_embeddings=[
            SampleEmbeddingCreate(
                sample_id=sample.sample_id,
                embedding_model_id=embedding_model_id,
                embedding=np.array([float(i), float(i + 1), float(i + 2)], dtype=np.float32),
            )
            for i, sample in enumerate(samples)
        ],
    )

    # Tag the first two samples, then load the collection filtered by that tag.
    tag = create_tag(session=db_session, collection_id=collection_id)
    tagged_sample_ids = [samples[0].sample_id, samples[1].sample_id]
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=tagged_sample_ids
    )

    filtered = sample_embedding_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        filters=SampleFilter(tag_ids=[tag.tag_id]),
    )

    # Only the tagged samples come back, with their embeddings intact.
    assert {row.sample_id for row in filtered} == set(tagged_sample_ids)
    embedding_by_id = {row.sample_id: list(row.embedding) for row in filtered}
    assert embedding_by_id[samples[0].sample_id] == [0.0, 1.0, 2.0]
    assert embedding_by_id[samples[1].sample_id] == [1.0, 2.0, 3.0]


def test_get_embedding_count(db_session: Session) -> None:
    # Create collections
    col1_id = create_collection(session=db_session).collection_id
    col2_id = create_collection(session=db_session, collection_name="col2").collection_id

    # Create samples.
    images_col1 = create_images(
        db_session=db_session,
        collection_id=col1_id,
        images=[ImageStub("sample1.png"), ImageStub("sample2.png"), ImageStub("sample3.png")],
    )
    create_images(db_session=db_session, collection_id=col2_id, images=[ImageStub("sample.png")])

    # Create an embedding models
    embedding_model_1 = create_embedding_model(session=db_session, collection_id=col1_id)
    embedding_model_1_id = embedding_model_1.embedding_model_id
    embedding_model_2 = create_embedding_model(session=db_session, collection_id=col1_id)
    embedding_model_2_id = embedding_model_2.embedding_model_id

    # Create embeddings for col1
    embedding_inputs = [
        SampleEmbeddingCreate(
            sample_id=images_col1[0].sample_id,
            embedding_model_id=embedding_model_1_id,
            embedding=np.array([0.0, 0.0, 0.0], dtype=np.float32),
        ),
        SampleEmbeddingCreate(
            sample_id=images_col1[1].sample_id,
            embedding_model_id=embedding_model_1_id,
            embedding=np.array([0.0, 0.0, 0.0], dtype=np.float32),
        ),
    ]
    sample_embedding_resolver.create_many(session=db_session, sample_embeddings=embedding_inputs)

    # Collection 1 has two embeddings
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session,
        collection_id=col1_id,
        embedding_model_id=embedding_model_1_id,
    )
    assert count == 2

    # Collection 2 has no embeddings
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session,
        collection_id=col2_id,
        embedding_model_id=embedding_model_2_id,
    )
    assert count == 0
