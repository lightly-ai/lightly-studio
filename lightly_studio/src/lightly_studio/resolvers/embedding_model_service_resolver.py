"""Handler for database operations related to embedding model services."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from lightly_studio.dataset import embedding_service
from lightly_studio.models.embedding_model_service import EmbeddingModelServiceTable


def get_by_model_hash(
    session: Session, embedding_model_hash: str
) -> EmbeddingModelServiceTable | None:
    """Retrieve the service serving the model with the given hash."""
    return session.exec(
        select(EmbeddingModelServiceTable).where(
            EmbeddingModelServiceTable.embedding_model_hash == embedding_model_hash
        )
    ).one_or_none()


def set_serving_url(
    session: Session, embedding_model_hash: str, serving_url: str
) -> EmbeddingModelServiceTable:
    """Point the given model at ``serving_url``, replacing any previous URL.

    Args:
        session: The database session.
        embedding_model_hash: Identifies the model the service serves.
        serving_url: Base URL of the embedding service.

    Returns:
        The stored service row.

    Raises:
        ValueError: If ``serving_url`` is not a valid embedding service URL.
    """
    validated_url = embedding_service.validate_serving_url(serving_url)

    service = get_by_model_hash(session=session, embedding_model_hash=embedding_model_hash)
    if service is None:
        service = EmbeddingModelServiceTable(
            embedding_model_hash=embedding_model_hash, serving_url=validated_url
        )
    else:
        service.serving_url = validated_url
        service.updated_at = datetime.now(timezone.utc)

    session.add(service)
    session.commit()
    session.refresh(service)
    return service


def delete_by_model_hash(session: Session, embedding_model_hash: str) -> bool:
    """Delete the service for the given model hash. Returns False if there was none."""
    service = get_by_model_hash(session=session, embedding_model_hash=embedding_model_hash)
    if service is None:
        return False

    session.delete(service)
    session.commit()
    return True
