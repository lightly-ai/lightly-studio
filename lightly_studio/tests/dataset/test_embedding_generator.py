from __future__ import annotations

from uuid import uuid4

from lightly_studio.dataset.embedding_generator import (
    ImageCrop,
    RandomEmbeddingGenerator,
)


class TestRandomEmbeddingGeneratorCrops:
    def test_embed_image_crops__returns_one_embedding_per_crop(self) -> None:
        generator = RandomEmbeddingGenerator(dimension=4)
        keys = [uuid4(), uuid4(), uuid4()]
        keyed_crops = [
            (keys[0], ImageCrop(filepath="a.jpg", x=0, y=0, width=10, height=10)),
            (keys[1], ImageCrop(filepath="a.jpg", x=5, y=5, width=20, height=20)),
            (keys[2], ImageCrop(filepath="b.jpg", x=0, y=0, width=30, height=30)),
        ]

        result = generator.embed_image_crops(keyed_crops)

        assert result.embeddings.shape == (3, 4)
        assert result.keys == keys

    def test_embed_image_crops__empty_input_returns_empty_array(self) -> None:
        generator = RandomEmbeddingGenerator(dimension=4)

        result = generator.embed_image_crops([])

        assert result.embeddings.shape == (0, 4)
        assert result.keys == []
