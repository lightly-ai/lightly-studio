from __future__ import annotations

from sqlmodel import Session

from lightly_studio.dataset import embedding_utils
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)


def test_get_collection_embeddings_status__no_models(db_session: Session) -> None:
    col_id = create_collection(session=db_session).collection_id

    status = embedding_utils.get_collection_embeddings_status(
        session=db_session, collection_id=col_id
    )
    assert status.has_embeddings is False
    assert status.has_text_search_embeddings is False


def test_get_collection_embeddings_status__model_without_embeddings(db_session: Session) -> None:
    col_id = create_collection(session=db_session).collection_id
    create_embedding_model(session=db_session, collection_id=col_id)

    status = embedding_utils.get_collection_embeddings_status(
        session=db_session, collection_id=col_id
    )
    assert status.has_embeddings is False
    assert status.has_text_search_embeddings is False


def test_get_collection_embeddings_status__text_capable_model(db_session: Session) -> None:
    col_id = create_collection(session=db_session).collection_id
    embedding_model_id = create_embedding_model(
        session=db_session, collection_id=col_id
    ).embedding_model_id
    create_samples_with_embeddings(
        session=db_session,
        collection_id=col_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[(ImageStub(), [0.1, 0.2, 0.3])],
    )

    status = embedding_utils.get_collection_embeddings_status(
        session=db_session, collection_id=col_id
    )
    assert status.has_embeddings is True
    assert status.has_text_search_embeddings is True


def test_get_collection_embeddings_status__custom_model_only(db_session: Session) -> None:
    col_id = create_collection(session=db_session).collection_id
    embedding_model_id = create_embedding_model(
        session=db_session, collection_id=col_id, supports_text_search=False
    ).embedding_model_id
    create_samples_with_embeddings(
        session=db_session,
        collection_id=col_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[(ImageStub(), [0.1, 0.2, 0.3])],
    )

    status = embedding_utils.get_collection_embeddings_status(
        session=db_session, collection_id=col_id
    )
    assert status.has_embeddings is True
    assert status.has_text_search_embeddings is False
