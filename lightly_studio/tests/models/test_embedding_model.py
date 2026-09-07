"""Tests for the EmbeddingModel secret handling."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from lightly_studio.models.embedding_model import EmbeddingModelCreate, EmbeddingModelTable
from lightly_studio.resolvers import embedding_model_resolver
from tests.helpers_resolvers import create_collection

_API_KEY = "super-secret-token"


def test_embedding_model_table__api_key_absent_from_repr(db_session: Session) -> None:
    """Dumping the row into a log line must not leak the API key."""
    collection = create_collection(session=db_session)
    embedding_model = embedding_model_resolver.create(
        session=db_session,
        embedding_model=EmbeddingModelCreate(
            dataset_id=collection.dataset_id,
            name="remote_model",
            embedding_dimension=128,
            remote_embedder_url="https://embedder.example.com",
            api_key=_API_KEY,
        ),
    )

    assert _API_KEY not in repr(embedding_model)
    assert _API_KEY not in str(embedding_model)
    assert "remote_model" in repr(embedding_model)


def test_embedding_model_table__api_key_absent_from_log_line(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """A log line that dumps the row must not contain the API key."""
    collection = create_collection(session=db_session)
    embedding_model = embedding_model_resolver.create(
        session=db_session,
        embedding_model=EmbeddingModelCreate(
            dataset_id=collection.dataset_id,
            name="remote_model",
            embedding_dimension=128,
            api_key=_API_KEY,
        ),
    )

    logger = logging.getLogger(__name__)
    with caplog.at_level(logging.INFO, logger=__name__):
        logger.info("Resolved embedding model %s", embedding_model)
        logger.info(f"Resolved embedding model {embedding_model}")

    assert _API_KEY not in caplog.text
    assert "remote_model" in caplog.text


def test_embedding_model_table__api_key_absent_from_response_models(
    test_client: TestClient,
) -> None:
    """No route may return the API key, so no response schema may declare it."""
    schemas = test_client.get("/openapi.json").json()["components"]["schemas"]

    leaking = [name for name, schema in schemas.items() if "api_key" in _properties(schema=schema)]
    assert leaking == []


def test_embedding_model_table__api_key_round_trips(db_session: Session) -> None:
    """The API key is persisted and readable through the resolver."""
    collection = create_collection(session=db_session)
    created = embedding_model_resolver.create(
        session=db_session,
        embedding_model=EmbeddingModelCreate(
            dataset_id=collection.dataset_id,
            name="remote_model",
            embedding_dimension=128,
            remote_embedder_url="https://embedder.example.com",
            api_key=_API_KEY,
        ),
    )

    stored = embedding_model_resolver.get_by_id(
        session=db_session, embedding_model_id=created.embedding_model_id
    )
    assert stored is not None
    assert stored.api_key == _API_KEY
    assert stored.remote_embedder_url == "https://embedder.example.com"


def test_embedding_model_table__api_key_defaults_to_none(db_session: Session) -> None:
    """A locally served model carries no API key."""
    collection = create_collection(session=db_session)
    created = embedding_model_resolver.create(
        session=db_session,
        embedding_model=EmbeddingModelCreate(
            dataset_id=collection.dataset_id,
            name="local_model",
            embedding_dimension=128,
        ),
    )

    assert created.api_key is None


def test_embedding_model_table__api_key_is_nullable() -> None:
    """The column must be nullable so existing rows need no backfill."""
    columns = SQLModel.metadata.tables[EmbeddingModelTable.__tablename__].columns
    assert columns["api_key"].nullable is True


def _properties(schema: dict[str, Any]) -> set[str]:
    """Collect the property names of a schema, including its `anyOf` and `allOf` branches."""
    names = set(schema.get("properties", {}))
    for branch in schema.get("anyOf", []) + schema.get("allOf", []) + schema.get("oneOf", []):
        names |= _properties(schema=branch)
    return names
