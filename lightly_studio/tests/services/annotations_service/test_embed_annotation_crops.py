from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.embed import embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import sample_embedding_resolver
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
)


@pytest.fixture
def _patched_registry(mocker: MockerFixture) -> None:
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)


@pytest.mark.usefixtures("_patched_registry")
def test_embed_annotation_crops(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=3,
        set_as_default=True,
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    box = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    classification = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    annotations_service.embed_annotation_crops(
        session=db_session, annotation_ids=[box.sample_id, classification.sample_id]
    )

    # Only the box has a crop, so only the box gets an embedding.
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session,
        sample_ids=[box.sample_id, classification.sample_id],
        embedding_model_id=model.embedding_model_id,
    )
    assert [row.sample_id for row in rows] == [box.sample_id]
