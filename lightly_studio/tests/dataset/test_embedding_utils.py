from __future__ import annotations

from sqlmodel import Session

from lightly_studio.dataset import embedding_utils
from lightly_studio.resolvers import embedding_model_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)


def test_collection_has_embeddings(db_session: Session) -> None:
    col_id = create_collection(session=db_session).collection_id
    embedding_model_id = create_embedding_model(
        session=db_session, collection_id=col_id
    ).embedding_model_id

    # Initially, the collection has no embeddings.
    assert not embedding_utils.collection_has_embeddings(
        session=db_session,
        collection_id=col_id,
    )

    # Add an embedding to the collection.
    create_samples_with_embeddings(
        session=db_session,
        collection_id=col_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[(ImageStub(), [0.1, 0.2, 0.3])],
    )

    # Now, the collection should report having embeddings.
    assert embedding_utils.collection_has_embeddings(
        session=db_session,
        collection_id=col_id,
    )


def test_collection_has_embeddings__does_not_register_a_model(db_session: Session) -> None:
    """Reading the flag must never write an embedding-model row.

    The collection's embedding-model row records what produced the stored vectors.
    Registering a model here would attribute custom-model embeddings to the built-in
    default and silently hide search.
    """
    col_id = create_collection(session=db_session).collection_id

    assert not embedding_utils.collection_has_embeddings(session=db_session, collection_id=col_id)

    assert (
        embedding_model_resolver.get_all_by_collection_id(session=db_session, collection_id=col_id)
        == []
    )


def test_collection_has_embeddings__custom_model(db_session: Session) -> None:
    """Embeddings from a model that is not loaded in-process still count."""
    col_id = create_collection(session=db_session).collection_id
    custom_model_id = create_embedding_model(
        session=db_session,
        collection_id=col_id,
        embedding_model_name="customer-model",
        embedding_model_hash="customer-model-v1",
    ).embedding_model_id
    create_samples_with_embeddings(
        session=db_session,
        collection_id=col_id,
        embedding_model_id=custom_model_id,
        images_and_embeddings=[(ImageStub(), [0.1, 0.2, 0.3])],
    )

    assert embedding_utils.collection_has_embeddings(session=db_session, collection_id=col_id)
