from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_get_unembedded_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other")
    model = create_embedding_model(
        session=db_session, collection_id=collection.collection_id, embedding_dimension=2
    )
    other_model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="other_model",
        embedding_dimension=2,
    )
    embedded = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )
    embedded_by_other_model = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/c.png"
    )
    unembedded = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.png"
    )
    # The resolver does not return an image of a different collection
    create_image(
        session=db_session, collection_id=other_collection.collection_id, file_path_abs="/d.png"
    )
    create_sample_embedding(
        session=db_session,
        sample_id=embedded.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0, 2.0],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=embedded_by_other_model.sample_id,
        embedding_model_id=other_model.embedding_model_id,
        embedding=[1.0, 2.0],
    )

    result = image_resolver.get_unembedded_sample_ids(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=model.embedding_model_id,
    )

    # The result is in the order of the image paths
    assert result == [unembedded.sample_id, embedded_by_other_model.sample_id]
