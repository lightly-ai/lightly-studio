from __future__ import annotations

from sqlmodel import Session

from lightly_studio.dataset import embedding_utils
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

    # Initially, the collection has an embedding model but no embeddings.
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


def test_collection_has_embeddings_without_model(db_session: Session) -> None:
    # A collection with no embedding model at all has no embeddings.
    col_id = create_collection(session=db_session).collection_id
    assert not embedding_utils.collection_has_embeddings(
        session=db_session,
        collection_id=col_id,
    )
