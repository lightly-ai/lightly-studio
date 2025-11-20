"""Test computing similarity."""

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.metadata import compute_similarity
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_dataset,
    create_embedding_model,
    create_samples_with_embeddings,
    create_tag,
)


def test_compute_similarity_metadata(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, dataset_name="similarity_test")
    dataset_id = dataset.dataset_id
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="example_embedding_model",
    )
    embedding_model_id = embedding_model.embedding_model_id
    samples = create_samples_with_embeddings(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="img0.jpg"), [1.0, 0.0, 0.0]),
            (ImageStub(path="img1.jpg"), [0.9, 0.0, 0.0]),
            (ImageStub(path="img2.jpg"), [0.0, 1.0, 0.0]),
            (ImageStub(path="img3.jpg"), [0.0, 0.0, 1.0]),
        ],
    )

    query_tag = create_tag(session=test_db, dataset_id=dataset_id, tag_name="query_tag")
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=query_tag.tag_id,
        sample_ids=[samples[0].sample_id, samples[2].sample_id],
    )

    compute_similarity.compute_similarity_metadata(
        session=test_db,
        key_dataset_id=dataset_id,
        embedding_model_id=embedding_model_id,
        query_tag_name="query_tag",
        metadata_name="similarity",
    )

    enriched_samples = list(DatasetQuery(dataset=dataset, session=test_db))
    # The nearest neighbor of embedding1 is embedding0 with distance 0.1.
    # The nearest neighbor of embedding3 is embedding2 with distance sqrt(2).
    # So similarity of sample1 should be higher than similarity of sample3.
    assert enriched_samples[1].metadata["similarity"] == pytest.approx(0.7678481)
    assert enriched_samples[3].metadata["similarity"] == pytest.approx(0.023853203)

    # The query samples have the maximum similarity value of 1.0.
    assert enriched_samples[0].metadata["similarity"] == 1.0
    assert enriched_samples[2].metadata["similarity"] == 1.0
