from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.dataset import embedding_utils
from lightly_studio.dataset.embedding_manager import EmbeddingManager
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)


def test_collection_has_embeddings(db_session: Session, mocker: MockerFixture) -> None:
    col_id = create_collection(session=db_session).collection_id
    embedding_model_id = create_embedding_model(
        session=db_session, collection_id=col_id
    ).embedding_model_id
    mock_get_model = mocker.patch.object(
        EmbeddingManager, "load_or_get_default_model", return_value=embedding_model_id
    )

    # Initially, the collection has no embeddings.
    assert not embedding_utils.collection_has_embeddings(
        session=db_session,
        collection_id=col_id,
    )
    mock_get_model.assert_called_once_with(
        session=db_session,
        collection_id=col_id,
    )
    mock_get_model.reset_mock()

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
    mock_get_model.assert_called_once_with(
        session=db_session,
        collection_id=col_id,
    )
