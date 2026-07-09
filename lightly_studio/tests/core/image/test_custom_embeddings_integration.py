"""Integration test for the "bring your own embeddings" workflow.

Guards the contract documented in `docs/docs/dataset_setup/image_dataset.md`: loading a
collection with `embed=False` and setting embeddings via `Sample.set_embedding(...)` must
(1) keep the custom embedding model as the collection's default (so the embedding plot
resolves to it) and (2) report `has_embeddings=True` but `has_text_search_embeddings=False`
(so the frontend shows the embedding plot but hides the text-search bar).
"""

from __future__ import annotations

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import embedding_utils
from lightly_studio.resolvers import embedding_model_resolver
from lightly_studio.resolvers.twodim_embedding_resolver import get_twodim_embeddings
from tests.helpers_resolvers import create_collection, create_image


def test_custom_embeddings_stay_default_and_hide_text_search(
    patch_collection: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    collection = create_collection(session=session)
    image_table = create_image(session=session, collection_id=collection.collection_id)
    sample = ImageSample(inner=image_table)

    # Simulate the recommended workflow: populate custom embeddings before ever
    # touching anything that could auto-register the built-in default model.
    sample.set_embedding([0.1, 0.2, 0.3])

    models = embedding_model_resolver.get_all_by_collection_id(
        session=session, collection_id=collection.collection_id
    )
    assert [m.name for m in models] == ["custom"]
    assert models[0].supports_text_search is False

    # The status the frontend uses to gate features: the embedding plot must be
    # available, text search must not.
    status = embedding_utils.get_collection_embeddings_status(
        session=session, collection_id=collection.collection_id
    )
    assert status.has_embeddings is True
    assert status.has_text_search_embeddings is False

    # The custom model must be the one the embedding plot resolves to.
    default_model = embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection.collection_id
    )
    assert default_model is not None
    assert default_model.name == "custom"

    # The embedding plot must resolve against the custom model and return one point.
    x_values, y_values, sample_ids = get_twodim_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=default_model.embedding_model_id,
    )
    assert len(x_values) == 1
    assert len(y_values) == 1
    assert sample_ids == [sample.sample_id]
