"""Tests for the embeddings2d status endpoint."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.resolvers import collection_embedding_model_resolver, twodim_embedding_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    fill_db_with_samples_and_embeddings,
)


def test_get_2d_embeddings_status__computed(test_client: TestClient, db_session: Session) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=3, embedding_model_names=["model_a"]
    )
    # The embedding writes leave a dirty placeholder row; overwrite it.
    db_session.merge(
        EmbeddingPlotTable(
            collection_id=collection_id,
            embedding_model_id=_default_model_id(session=db_session, collection_id=collection_id),
            is_dirty=False,
        )
    )
    db_session.commit()

    response = test_client.get(f"/api/collections/{collection_id}/embeddings2d/status")

    assert response.status_code == 200
    assert response.json() == {"is_computed": True, "embedding_count": 3}


def test_get_2d_embeddings_status__not_computed(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=3, embedding_model_names=["model_a"]
    )

    response = test_client.get(f"/api/collections/{collection_id}/embeddings2d/status")

    assert response.status_code == 200
    assert response.json() == {"is_computed": False, "embedding_count": 3}


def test_get_2d_embeddings_status__dirty(test_client: TestClient, db_session: Session) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=3, embedding_model_names=["model_a"]
    )
    # The embedding writes leave a dirty placeholder row; overwrite it.
    db_session.merge(
        EmbeddingPlotTable(
            collection_id=collection_id,
            embedding_model_id=_default_model_id(session=db_session, collection_id=collection_id),
            is_dirty=True,
        )
    )
    db_session.commit()

    response = test_client.get(f"/api/collections/{collection_id}/embeddings2d/status")

    assert response.json() == {"is_computed": False, "embedding_count": 3}


def test_get_2d_embeddings_status__counts_default_model_only(
    test_client: TestClient, db_session: Session
) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=3, embedding_model_names=["model_a", "model_b"]
    )

    response = test_client.get(f"/api/collections/{collection_id}/embeddings2d/status")

    assert response.json() == {"is_computed": False, "embedding_count": 3}


def test_get_2d_embeddings_status__no_embeddings(
    test_client: TestClient, db_session: Session
) -> None:
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session, collection_id=collection.collection_id, set_as_default=True
    )

    response = test_client.get(f"/api/collections/{collection.collection_id}/embeddings2d/status")

    assert response.status_code == 200
    assert response.json() == {"is_computed": False, "embedding_count": 0}


def test_get_2d_embeddings_status__unknown_collection(test_client: TestClient) -> None:
    response = test_client.get(f"/api/collections/{uuid4()}/embeddings2d/status")

    assert response.status_code == 404


def test_get_2d_embeddings_status__does_not_compute(
    test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=3, embedding_model_names=["model_a"]
    )
    get_plot = mocker.patch.object(
        twodim_embedding_resolver, "get_plot", side_effect=AssertionError
    )
    get_twodim_embeddings = mocker.patch.object(
        twodim_embedding_resolver, "get_twodim_embeddings", side_effect=AssertionError
    )

    response = test_client.get(f"/api/collections/{collection_id}/embeddings2d/status")

    assert response.json() == {"is_computed": False, "embedding_count": 3}
    get_plot.assert_not_called()
    get_twodim_embeddings.assert_not_called()


def _default_model_id(session: Session, collection_id: UUID) -> UUID:
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )
    assert model_id is not None
    return model_id
