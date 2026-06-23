from __future__ import annotations

from lightly_studio.dataset.embedding_generator import (
    ImageCrop,
    RandomEmbeddingGenerator,
)


class TestRandomEmbeddingGeneratorCrops:
    def test_embed_image_crops__returns_one_embedding_per_crop(self) -> None:
        generator = RandomEmbeddingGenerator(dimension=4)
        image_crops = [
            ImageCrop(filepath="a.jpg", x=0, y=0, width=10, height=10),
            ImageCrop(filepath="a.jpg", x=5, y=5, width=20, height=20),
            ImageCrop(filepath="b.jpg", x=0, y=0, width=30, height=30),
        ]

        embeddings = generator.embed_image_crops(image_crops)

        assert embeddings.shape == (3, 4)

    def test_embed_image_crops__empty_input_returns_empty_array(self) -> None:
        generator = RandomEmbeddingGenerator(dimension=4)

        embeddings = generator.embed_image_crops([])

        assert embeddings.shape == (0, 4)
