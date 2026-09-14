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

    link = collection_embedding_model_resolver.get_or_add_collection_model(
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
    collection_embedding_model_resolver.get_or_add_collection_model(
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
    link = collection_embedding_model_resolver.get_or_add_collection_model(
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
    collection_embedding_model_resolver.get_or_add_collection_model(
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
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_2",
    )
    for model in (model_1, model_2):
        collection_embedding_model_resolver.get_or_add_collection_model(
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


def test_has_default_by_collection_id__false_when_unset(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    assert not collection_embedding_model_resolver.has_default_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )


def test_has_default_by_collection_id__true_when_set(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session, collection_id=collection.collection_id, set_as_default=True
    )

    assert collection_embedding_model_resolver.has_default_by_collection_id(
        session=db_session, collection_id=collection.collection_id
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
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="model_2",
    )
    for model in (model_1, model_2):
        collection_embedding_model_resolver.get_or_add_collection_model(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=model.embedding_model_id,
        )

    linked = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )

    assert set(linked) == {model_1.embedding_model_id, model_2.embedding_model_id}


def test_get_model_id_by_name__none_returns_default(db_session: Session) -> None:
    """Resolve the default model id when the name is None."""
    collection = create_collection(session=db_session)
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_1",
        set_as_default=True,
    )

    result = collection_embedding_model_resolver.get_model_id_by_name(
        session=db_session, collection_id=collection.collection_id, embedding_model_name=None
    )

    assert result == embedding_model.embedding_model_id


def test_get_model_id_by_name__none_returns_default_not_oldest(db_session: Session) -> None:
    """Resolve the default model, not the oldest, when the collection has several."""
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="oldest_model",
    )
    default_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="default_model",
        set_as_default=True,
    )

    result = collection_embedding_model_resolver.get_model_id_by_name(
        session=db_session, collection_id=collection.collection_id, embedding_model_name=None
    )

    assert result == default_model.embedding_model_id


def test_get_model_id_by_name__none_without_default(db_session: Session) -> None:
    """Raise when the name is None but no linked model is the default."""
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_1",
    )

    with pytest.raises(ValueError, match=r"has no default embedding model"):
        collection_embedding_model_resolver.get_model_id_by_name(
            session=db_session, collection_id=collection.collection_id, embedding_model_name=None
        )


def test_get_model_id_by_name__none_with_no_models(db_session: Session) -> None:
    """Raise when the name is None but the collection has no linked model."""
    collection = create_collection(session=db_session)

    with pytest.raises(ValueError, match=r"has no default embedding model"):
        collection_embedding_model_resolver.get_model_id_by_name(
            session=db_session, collection_id=collection.collection_id, embedding_model_name=None
        )


def test_get_model_id_by_name__existing_name(db_session: Session) -> None:
    """Resolve a linked model id by its name."""
    collection = create_collection(session=db_session)
    model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_1",
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_2",
    )

    result_1 = collection_embedding_model_resolver.get_model_id_by_name(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_1",
    )
    assert result_1 == model_1.embedding_model_id

    result_2 = collection_embedding_model_resolver.get_model_id_by_name(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_2",
    )
    assert result_2 == model_2.embedding_model_id


def test_get_model_id_by_name__nonexistent_name(db_session: Session) -> None:
    """Raise when no linked model has the given name."""
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="embedding_model_1",
    )

    with pytest.raises(ValueError, match=r"Embedding model with name `nonexistent` not found."):
        collection_embedding_model_resolver.get_model_id_by_name(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_name="nonexistent",
        )


def test_get_model_id_by_name__scoped_to_the_collection(db_session: Session) -> None:
    """Membership comes from the link table, so another collection's model is not resolved."""
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=other_collection.collection_id,
        embedding_model_name="other_model",
    )

    with pytest.raises(ValueError, match=r"has no default embedding model"):
        collection_embedding_model_resolver.get_model_id_by_name(
            session=db_session, collection_id=collection.collection_id, embedding_model_name=None
        )

    with pytest.raises(ValueError, match=r"Embedding model with name `other_model` not found."):
        collection_embedding_model_resolver.get_model_id_by_name(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_name="other_model",
        )
