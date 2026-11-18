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
    create_image,
    create_sample_embedding,
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
    assert response.json() == {"is_computed": True, "embedding_count": None}


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
    collection = create_collection(session=db_session)
    default_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_a",
        embedding_dimension=2,
        set_as_default=True,
    )
    other_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_b",
        embedding_dimension=2,
    )
    first = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )
    second = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.png"
    )
    # The default model has 1 embedding, the other model has 2.
    create_sample_embedding(
        session=db_session,
        sample_id=first.sample_id,
        embedding_model_id=default_model.embedding_model_id,
        embedding=[1.0, 2.0],
    )
    for image in (first, second):
        create_sample_embedding(
            session=db_session,
            sample_id=image.sample_id,
            embedding_model_id=other_model.embedding_model_id,
            embedding=[1.0, 2.0],
        )

    response = test_client.get(f"/api/collections/{collection.collection_id}/embeddings2d/status")

    assert response.json() == {"is_computed": False, "embedding_count": 1}


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


def test_get_2d_embeddings_status__no_default_model(
    test_client: TestClient, db_session: Session
) -> None:
    collection = create_collection(session=db_session)

    response = test_client.get(f"/api/collections/{collection.collection_id}/embeddings2d/status")

    assert response.status_code == 404


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
