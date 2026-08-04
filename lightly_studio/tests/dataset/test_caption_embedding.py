"""Unit tests for caption embedding generation."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlmodel import Session

from lightly_studio.dataset import caption_embedding
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import (
    caption_resolver,
    collection_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_embed_captions(db_session: Session, collection: CollectionTable) -> None:
    """Captions passed by ID are embedded with the caption collection's default model."""
    caption_sample_ids = _create_captions(
        session=db_session, collection_id=collection.collection_id, texts=["a person walks"]
    )
    manager = EmbeddingManagerProvider.get_embedding_manager()

    caption_embedding.embed_captions(session=db_session, caption_sample_ids=caption_sample_ids)

    model_id = manager.load_or_get_default_model(
        session=db_session,
        collection_id=_caption_collection_id(
            session=db_session, collection_id=collection.collection_id
        ),
    )
    assert model_id is not None
    stored_embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=caption_sample_ids, embedding_model_id=model_id
    )
    assert len(stored_embeddings) == 1


def test_embed_captions__no_captions(db_session: Session) -> None:
    """Embedding no captions is a no-op and does not need a model."""
    caption_embedding.embed_captions(session=db_session, caption_sample_ids=[])


def test_embed_captions__unknown_caption(db_session: Session) -> None:
    """An unknown caption ID is ignored instead of raising."""
    caption_embedding.embed_captions(session=db_session, caption_sample_ids=[uuid4()])


def test_embed_collection_captions(db_session: Session, collection: CollectionTable) -> None:
    """All captions of the collection are embedded."""
    caption_sample_ids = _create_captions(
        session=db_session,
        collection_id=collection.collection_id,
        texts=["a person walks", "a dog runs"],
    )
    manager = EmbeddingManagerProvider.get_embedding_manager()

    caption_embedding.embed_collection_captions(
        session=db_session, root_collection_id=collection.collection_id
    )

    model_id = manager.load_or_get_default_model(
        session=db_session,
        collection_id=_caption_collection_id(
            session=db_session, collection_id=collection.collection_id
        ),
    )
    assert model_id is not None
    stored_embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=caption_sample_ids, embedding_model_id=model_id
    )
    assert len(stored_embeddings) == 2


def test_embed_collection_captions__collection_without_captions(db_session: Session) -> None:
    """A collection that never had captions has no caption collection to embed."""
    collection = create_collection(session=db_session)

    caption_embedding.embed_collection_captions(
        session=db_session, root_collection_id=collection.collection_id
    )

    assert (
        collection_resolver.get_by_name(
            session=db_session,
            name=SampleType.CAPTION.value.lower(),
            parent_collection_id=collection.collection_id,
        )
        is None
    )


def _create_captions(session: Session, collection_id: UUID, texts: list[str]) -> list[UUID]:
    """Create captions on a new image of the collection."""
    image = create_image(session=session, collection_id=collection_id)
    return caption_resolver.create_many(
        session=session,
        parent_collection_id=collection_id,
        captions=[CaptionCreate(parent_sample_id=image.sample_id, text=text) for text in texts],
    )


def _caption_collection_id(session: Session, collection_id: UUID) -> UUID:
    return collection_resolver.get_or_create_child_collection(
        session=session, collection_id=collection_id, sample_type=SampleType.CAPTION
    )
