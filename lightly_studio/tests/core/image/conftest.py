from __future__ import annotations

import pytest

from lightly_studio import ImageDataset
from lightly_studio.embed.random_embedder import RandomEmbedder
from tests.helpers_resolvers import create_embedding_model


@pytest.fixture
def dataset_with_mismatched_embedder(patch_collection: None) -> ImageDataset:  # noqa: ARG001
    """An empty image dataset whose embeddings have another dimension than the embedder.

    ``patch_collection`` registers a ``RandomEmbedder`` with the default dimension. The
    dataset stores the space of that embedder with one dimension more, the way a wrongly
    registered embedder finds it.
    """
    spec = RandomEmbedder().embedding_space_spec()
    dataset = ImageDataset.create(name="test_dataset")
    create_embedding_model(
        session=dataset.session,
        collection_id=dataset.collection_id,
        embedding_model_name=spec.space_key,
        embedding_dimension=spec.dimension + 1,
        set_as_default=True,
    )
    return dataset
