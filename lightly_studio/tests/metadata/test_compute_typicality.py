"""Test computing typicality."""

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.metadata import compute_typicality
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)


def test_compute_typicality_metadata(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    create_samples_with_embeddings(
        session=test_db,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="img0.jpg"), [1.0, 0.0, 0.0]),
            (ImageStub(path="img1.jpg"), [0.0, 1.0, 0.0]),
            (ImageStub(path="img2.jpg"), [0.0, 1.0, 1.0]),
        ],
    )

    # Distances are 1, sqrt(2) and sqrt(3). The most typical is the second embedding, as it's the
    # closest to both (1 and sqrt(2)). The 3rd one has distances 1 and sqrt(3), so it's the second
    # most typical.
    compute_typicality.compute_typicality_metadata(
        session=test_db, collection_id=collection_id, embedding_model_id=embedding_model_id
    )

    samples = list(DatasetQuery(collection, test_db))
    assert samples[0].metadata["typicality"] == pytest.approx(0.3225063)
    assert samples[1].metadata["typicality"] == pytest.approx(0.4222289)
    assert samples[2].metadata["typicality"] == pytest.approx(0.3853082)
