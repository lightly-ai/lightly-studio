from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_embedding_model_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
)


def test_set_default__inserts(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)

    default = collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    assert default.collection_id == collection.collection_id
    assert default.embedding_model_id == model.embedding_model_id


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

    # The collection still has a single default, now pointing at the second model.
    assert (
        collection_embedding_model_resolver.get_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model_2.embedding_model_id
    )


def test_get_by_collection_id__none_when_unset(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    assert (
        collection_embedding_model_resolver.get_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )


def test_get_by_collection_id__returns_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)
    collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    assert (
        collection_embedding_model_resolver.get_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model.embedding_model_id
    )


def test_delete_by_collection_id__deletes(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(session=db_session, collection_id=collection.collection_id)
    collection_embedding_model_resolver.set_default(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    deleted = collection_embedding_model_resolver.delete_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )

    assert deleted is True
    assert (
        collection_embedding_model_resolver.get_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )


def test_delete_by_collection_id__returns_false_when_absent(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    assert (
        collection_embedding_model_resolver.delete_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is False
    )
