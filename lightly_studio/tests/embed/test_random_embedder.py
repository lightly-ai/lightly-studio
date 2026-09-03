import numpy as np
from PIL import Image

from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.embed.types import ImageCrop


class TestRandomEmbedder:
    def test_embedding_space_spec(self) -> None:
        embedder = RandomEmbedder(dimension=5)

        spec = embedder.embedding_space_spec()

        assert spec.space_key == "random_model"
        assert spec.dimension == 5

    def test_embed_images(self) -> None:
        embedder = RandomEmbedder(dimension=4)

        result = embedder.embed_images(paths=["a.jpg", "b.jpg"])

        assert result.embeddings.shape == (2, 4)
        assert result.embeddings.dtype == np.float32
        assert result.kept_indices == [0, 1]

    def test_embed_crops(self) -> None:
        embedder = RandomEmbedder(dimension=4)
        crop = ImageCrop(filepath="a.jpg", x=0, y=0, width=1, height=1)

        result = embedder.embed_crops(crops=[crop])

        assert result.embeddings.shape == (1, 4)
        assert result.kept_indices == [0]

    def test_embed_videos(self) -> None:
        embedder = RandomEmbedder(dimension=4)

        result = embedder.embed_videos(paths=["a.mp4", "b.mp4", "c.mp4"])

        assert result.embeddings.shape == (3, 4)
        assert result.kept_indices == [0, 1, 2]

    def test_embed_frames(self) -> None:
        embedder = RandomEmbedder(dimension=4)
        frames = [Image.new("RGB", (2, 2))]

        result = embedder.embed_frames(frames=frames)

        assert result.embeddings.shape == (1, 4)
        assert result.kept_indices == [0]

    def test_embed_text(self) -> None:
        embedder = RandomEmbedder(dimension=4)

        result = embedder.embed_text(texts=["cat", "dog"])

        assert result.embeddings.shape == (2, 4)
        assert result.kept_indices == [0, 1]

    def test_embed_image_bytes(self) -> None:
        embedder = RandomEmbedder(dimension=4)

        result = embedder.embed_image_bytes(images=[b"data"])

        assert result.embeddings.shape == (1, 4)
        assert result.kept_indices == [0]
