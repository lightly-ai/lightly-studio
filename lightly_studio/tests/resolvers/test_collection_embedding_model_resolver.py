from __future__ import annotations

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.resolvers import collection_embedding_model_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
)


def test_get_or_create__links_model(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)

    link = collection_embedding_model_resolver.get_or_create(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    assert link.collection_id == collection.collection_id
    assert link.embedding_model_id == model.embedding_model_id
    # Linking never makes a model the default on its own.
    assert link.is_default is False


def test_get_or_create__idempotent_keeps_default(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)
    collection_embedding_model_resolver.get_or_create(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )
    collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    # Re-linking an already-default model returns the same row without clearing its flag.
    link = collection_embedding_model_resolver.get_or_create(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    assert link.is_default is True
    all_links = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert len(all_links) == 1


def test_set_default__flags_linked_model(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)
    collection_embedding_model_resolver.get_or_create(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    default = collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    assert default.embedding_model_id == model.embedding_model_id
    assert default.is_default is True


def test_set_default__replaces_existing(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_1",
        embedding_model_hash="hash_1",
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_2",
        embedding_model_hash="hash_2",
    )
    for model in (model_1, model_2):
        collection_embedding_model_resolver.get_or_create(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=model.embedding_model_id,
        )

    collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model_1.embedding_model_id,
    )
    collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model_2.embedding_model_id,
    )

    # The old default is demoted, so a single default holds and points at the second model.
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model_2.embedding_model_id
    )
    defaults = db_session.exec(
        select(CollectionEmbeddingModelTable).where(
            CollectionEmbeddingModelTable.collection_id == collection.collection_id,
            col(CollectionEmbeddingModelTable.is_default).is_(True),
        )
    ).all()
    assert [row.embedding_model_id for row in defaults] == [model_2.embedding_model_id]


def test_set_default__raises_when_unlinked(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)

    # The model exists but was never linked, so flagging it as default is a caller bug.
    with pytest.raises(ValueError, match="not linked"):
        collection_embedding_model_resolver.set_default(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=model.embedding_model_id,
        )


def test_get_default_by_collection_id__none_when_unset(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )


def test_get_default_by_collection_id__returns_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(
        session=db_session, collection_id=collection.collection_id, set_as_default=True
    )

    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model.embedding_model_id
    )


def test_get_all_by_collection_id__empty(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    assert (
        collection_embedding_model_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == []
    )


def test_get_all_by_collection_id__returns_all_linked(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_1",
        embedding_model_hash="hash_1",
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_2",
        embedding_model_hash="hash_2",
    )
    for model in (model_1, model_2):
        collection_embedding_model_resolver.get_or_create(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=model.embedding_model_id,
        )

    linked = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )

    assert set(linked) == {model_1.embedding_model_id, model_2.embedding_model_id}
