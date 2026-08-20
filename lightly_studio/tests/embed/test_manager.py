from __future__ import annotations

import numpy as np
from sqlmodel import Session

from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.embed.base_embedder import BaseEmbedder
from lightly_studio.embed.capability import EmbedderDescriptor
from lightly_studio.embed.manager import EmbedderManager
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import embedding_model_resolver, sample_embedding_resolver


class _CustomEmbedder(BaseEmbedder):
    """Image-path embedder with a distinctive dimension for override tests."""

    def load(self) -> EmbedderDescriptor:
        return self._descriptor(model_id="custom", dimension=8)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 8), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class _CountingLoadEmbedder(BaseEmbedder):
    """Image-path embedder that counts how often ``load`` is called."""

    def __init__(self) -> None:
        self.load_count = 0

    def load(self) -> EmbedderDescriptor:
        self.load_count += 1
        return self._descriptor(model_id="counting", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 3), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


class TestEmbedderManager:
    def test_embed_images_and_store(
        self,
        db_session: Session,
        collection: CollectionTable,
        samples: list[ImageTable],
    ) -> None:
        manager = EmbedderManager()
        sample_ids = [sample.sample_id for sample in samples]

        manager.embed_images_and_store(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )

        models = embedding_model_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        assert len(models) == 1
        assert models[0].embedding_dimension == 3
        stored = sample_embedding_resolver.get_by_sample_ids(
            session=db_session,
            sample_ids=sample_ids,
            embedding_model_id=models[0].embedding_model_id,
        )
        assert len(stored) == len(samples)

    def test_embed_images_and_store__empty_sample_ids(
        self,
        db_session: Session,
        collection: CollectionTable,
    ) -> None:
        manager = EmbedderManager()

        manager.embed_images_and_store(
            session=db_session, collection_id=collection.collection_id, sample_ids=[]
        )

        models = embedding_model_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        assert models == []

    def test_register__overrides_default(
        self,
        db_session: Session,
        collection: CollectionTable,
        samples: list[ImageTable],
    ) -> None:
        manager = EmbedderManager()
        manager.register(_CustomEmbedder())
        sample_ids = [sample.sample_id for sample in samples]

        manager.embed_images_and_store(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )

        models = embedding_model_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        assert len(models) == 1
        assert models[0].name == "custom"
        assert models[0].embedding_dimension == 8

    def test_load_once__loads_only_once(self) -> None:
        manager = EmbedderManager()
        embedder = _CountingLoadEmbedder()

        first = manager._load_once(embedder)
        second = manager._load_once(embedder)

        assert embedder.load_count == 1
        assert first is second
        assert first.model_id == "counting"
