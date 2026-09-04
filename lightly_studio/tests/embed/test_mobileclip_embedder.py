from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from lightly_studio.embed.mobileclip_embedder import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    MobileCLIPEmbedder,
)
from lightly_studio.embed.types import ImageCrop

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestMobileCLIPEmbedder:
    def test_embedding_space_spec(self) -> None:
        mobileclip = MobileCLIPEmbedder()
        space_spec = mobileclip.embedding_space_spec()

        assert space_spec.space_key == MODEL_NAME
        assert space_spec.dimension == EMBEDDING_DIMENSION

    def test_embed_images(self) -> None:
        mobileclip = MobileCLIPEmbedder()
        cat_image_path = FIXTURES_DIR / "cat.jpg"

        result = mobileclip.embed_images(paths=[str(cat_image_path)])

        assert result.kept_indices == [0]
        assert result.embeddings.shape == (1, 512)

        # Normalise and test a few values.
        cat_embedding_normed = result.embeddings[0]
        cat_embedding_normed /= np.linalg.norm(cat_embedding_normed)
        assert np.isclose(cat_embedding_normed[0], 0.0418, atol=1e-4)
        assert np.isclose(cat_embedding_normed[1], 0.0563, atol=1e-4)
        assert np.isclose(cat_embedding_normed[2], -0.0272, atol=1e-4)
        assert np.isclose(cat_embedding_normed[3], 0.0319, atol=1e-4)

    def test_embed_image_crops__empty_input(self) -> None:
        mobileclip = MobileCLIPEmbedder()

        result = mobileclip.embed_image_crops(crops=[])

        assert result.embeddings.shape == (0, 512)
        assert result.kept_indices == []

    def test_embed_image_crops__full_image_crop_matches_embed_images(self) -> None:
        mobileclip = MobileCLIPEmbedder()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        with Image.open(cat_image_path) as image:
            width, height = image.size

        full_crop = ImageCrop(filepath=str(cat_image_path), x=0, y=0, width=width, height=height)
        crop_result = mobileclip.embed_image_crops(crops=[full_crop])
        image_result = mobileclip.embed_images(paths=[str(cat_image_path)])

        assert crop_result.embeddings.shape == (1, 512)
        assert crop_result.kept_indices == [0]
        # A crop covering the entire image is preprocessed and encoded identically
        # to the full image, so the embeddings must match.
        assert np.allclose(crop_result.embeddings[0], image_result.embeddings[0], atol=1e-4)

    def test_embed_frames__empty_input(self) -> None:
        mobileclip = MobileCLIPEmbedder()

        result = mobileclip.embed_frames(frames=[])

        assert result.embeddings.shape == (0, 512)
        assert result.kept_indices == []

    def test_embed_frames__matches_embed_images(self) -> None:
        mobileclip = MobileCLIPEmbedder()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        with Image.open(cat_image_path) as image:
            cat_pil_image = image.convert("RGB")

        frame_result = mobileclip.embed_frames(frames=[cat_pil_image])
        image_result = mobileclip.embed_images(paths=[str(cat_image_path)])

        assert frame_result.embeddings.shape == (1, 512)
        assert frame_result.kept_indices == [0]
        # An in-memory PIL image is preprocessed and encoded identically to the same
        # image loaded from disk, so the embeddings must match.
        assert np.allclose(frame_result.embeddings[0], image_result.embeddings[0], atol=1e-4)

    def test_embed_text(self) -> None:
        mobileclip = MobileCLIPEmbedder()

        result = mobileclip.embed_text(texts=["a cat"])

        assert result.kept_indices == [0]
        assert result.embeddings.shape == (1, 512)

        # Normalise and test a few values.
        embedding_normed = result.embeddings[0]
        embedding_normed /= np.linalg.norm(embedding_normed)
        assert np.isclose(embedding_normed[0], 0.0072, atol=1e-4)
        assert np.isclose(embedding_normed[1], 0.0242, atol=1e-4)
        assert np.isclose(embedding_normed[2], 0.0922, atol=1e-4)
        assert np.isclose(embedding_normed[3], 0.0159, atol=1e-4)

    def test_embed_text__empty_input(self) -> None:
        mobileclip = MobileCLIPEmbedder()

        result = mobileclip.embed_text(texts=[])

        assert result.embeddings.shape == (0, 512)
        assert result.embeddings.dtype == np.float32
        assert result.kept_indices == []

    def test_classification(self) -> None:
        """End-to-end test for embedding consistency.

        Embed texts "a cat", "a dog" and "a tiger". Compare with
        "cat.jpg" image embedding using cosine distance.
        Pick a classification with softmax.
        """
        mobileclip = MobileCLIPEmbedder()

        # Embed texts.
        text_emb = torch.from_numpy(
            mobileclip.embed_text(texts=["a cat", "a dog", "a tiger"]).embeddings
        )
        text_emb /= text_emb.norm(dim=-1, keepdim=True)

        # Embed image.
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        cat_image_emb = torch.from_numpy(
            mobileclip.embed_images(paths=[str(cat_image_path)]).embeddings[0]
        )
        cat_image_emb /= cat_image_emb.norm(dim=-1, keepdim=True)

        # Compute softmax similarity as in ml-mobileclip repo example.
        text_probs = (100.0 * cat_image_emb @ text_emb.T).softmax(dim=-1)
        assert np.isclose(text_probs[0], 1.0, atol=1e-3)
        assert np.isclose(text_probs[1], 0.0, atol=1e-3)
        assert np.isclose(text_probs[2], 0.0, atol=1e-3)
