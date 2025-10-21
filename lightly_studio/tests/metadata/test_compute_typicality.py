"""Test computing typicality."""

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.metadata import compute_typicality
from tests.helpers_resolvers import (
    create_dataset,
    create_embedding_model,
    create_sample,
    create_sample_embedding,
)


def test_compute_typicality_metadata(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 1.0, 1.0],
    ]
    for i, embedding in enumerate(embeddings):
        sample = create_sample(
            session=test_db, dataset_id=dataset_id, file_path_abs=f"sample{i}.jpg"
        )
        create_sample_embedding(
            session=test_db,
            sample_id=sample.sample_id,
            embedding=embedding,
            embedding_model_id=embedding_model_id,
        )

    # Distances are 1, sqrt(2) and sqrt(3). The most typical is the second embedding, as it's the
    # closest to both (1 and sqrt(2)). The 3rd one has distances 1 and sqrt(3), so it's the second
    # most typical.
    compute_typicality.compute_typicality_metadata(
        session=test_db, dataset_id=dataset_id, embedding_model_id=embedding_model_id
    )

    samples = list(DatasetQuery(dataset, test_db))
    assert samples[0].metadata["typicality"] == pytest.approx(0.3225063)
    assert samples[1].metadata["typicality"] == pytest.approx(0.4222289)
    assert samples[2].metadata["typicality"] == pytest.approx(0.3853082)
