from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import embedding_model_service_resolver


def test_get_by_model_hash__missing(db_session: Session) -> None:
    assert (
        embedding_model_service_resolver.get_by_model_hash(
            session=db_session, embedding_model_hash="customer-model-v1"
        )
        is None
    )


def test_set_serving_url(db_session: Session) -> None:
    service = embedding_model_service_resolver.set_serving_url(
        session=db_session,
        embedding_model_hash="customer-model-v1",
        serving_url="https://embeddings.corp.example",
    )

    assert service.serving_url == "https://embeddings.corp.example"
    stored = embedding_model_service_resolver.get_by_model_hash(
        session=db_session, embedding_model_hash="customer-model-v1"
    )
    assert stored is not None
    assert stored.embedding_model_service_id == service.embedding_model_service_id


def test_set_serving_url__updates_existing(db_session: Session) -> None:
    """A hostname change is one update, not a new row per collection using the model."""
    created = embedding_model_service_resolver.set_serving_url(
        session=db_session,
        embedding_model_hash="customer-model-v1",
        serving_url="https://old.corp.example",
    )

    updated = embedding_model_service_resolver.set_serving_url(
        session=db_session,
        embedding_model_hash="customer-model-v1",
        serving_url="https://new.corp.example",
    )

    assert updated.embedding_model_service_id == created.embedding_model_service_id
    assert updated.serving_url == "https://new.corp.example"


def test_set_serving_url__rejects_insecure_url(db_session: Session) -> None:
    try:
        embedding_model_service_resolver.set_serving_url(
            session=db_session,
            embedding_model_hash="customer-model-v1",
            serving_url="http://192.168.1.20:8123",
        )
        raise AssertionError("Expected a ValueError for a non-loopback http URL.")
    except ValueError:
        pass

    assert (
        embedding_model_service_resolver.get_by_model_hash(
            session=db_session, embedding_model_hash="customer-model-v1"
        )
        is None
    )


def test_delete_by_model_hash(db_session: Session) -> None:
    embedding_model_service_resolver.set_serving_url(
        session=db_session,
        embedding_model_hash="customer-model-v1",
        serving_url="https://embeddings.corp.example",
    )

    assert embedding_model_service_resolver.delete_by_model_hash(
        session=db_session, embedding_model_hash="customer-model-v1"
    )
    assert (
        embedding_model_service_resolver.get_by_model_hash(
            session=db_session, embedding_model_hash="customer-model-v1"
        )
        is None
    )


def test_delete_by_model_hash__missing(db_session: Session) -> None:
    assert not embedding_model_service_resolver.delete_by_model_hash(
        session=db_session, embedding_model_hash="customer-model-v1"
    )
