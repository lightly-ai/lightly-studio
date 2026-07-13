from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.dataset.mobileclip_embedding_generator import (
    MobileCLIPEmbeddingGenerator,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestMobileCLIPEmbeddingGenerator:
    def test_get_embedding_model_input(self) -> None:
        mobileclip = MobileCLIPEmbeddingGenerator()
        collection_id = uuid.uuid4()
        embedding_model_input = mobileclip.get_embedding_model_input(collection_id=collection_id)

        assert embedding_model_input.name == "mobileclip_s0"
        assert embedding_model_input.embedding_dimension == 512
        assert embedding_model_input.collection_id == collection_id
        assert embedding_model_input.embedding_model_hash != ""

    def test_embed_text(self) -> None:
        text = "a cat"
        mobileclip = MobileCLIPEmbeddingGenerator()
        embedding = mobileclip.embed_text(text)
        assert len(embedding) == 512

        # Normalise and test a few values.
        embedding_normed = np.array(embedding)
        embedding_normed /= np.linalg.norm(embedding_normed)
        assert np.isclose(embedding_normed[0], 0.0072, atol=1e-4)
        assert np.isclose(embedding_normed[1], 0.0242, atol=1e-4)
        assert np.isclose(embedding_normed[2], 0.0922, atol=1e-4)
        assert np.isclose(embedding_normed[3], 0.0159, atol=1e-4)

    def test_embed_images(self) -> None:
        mobileclip = MobileCLIPEmbeddingGenerator()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        embeddings = mobileclip.embed_images([str(cat_image_path)])

        assert len(embeddings) == 1
        cat_embedding = embeddings[0]
        assert len(cat_embedding) == 512

        # Normalise and test a few values.
        cat_embedding_normed = np.array(cat_embedding)
        cat_embedding_normed /= np.linalg.norm(cat_embedding_normed)
        assert np.isclose(cat_embedding_normed[0], 0.0418, atol=1e-4)
        assert np.isclose(cat_embedding_normed[1], 0.0563, atol=1e-4)
        assert np.isclose(cat_embedding_normed[2], -0.0272, atol=1e-4)
        assert np.isclose(cat_embedding_normed[3], 0.0319, atol=1e-4)

    def test_embed_image_crops__empty_input(self) -> None:
        mobileclip = MobileCLIPEmbeddingGenerator()
        embeddings = mobileclip.embed_image_crops([])

        assert embeddings.shape == (0, 512)

    def test_embed_image_crops__full_image_crop_matches_embed_images(self) -> None:
        mobileclip = MobileCLIPEmbeddingGenerator()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        with Image.open(cat_image_path) as image:
            width, height = image.size

        full_crop = ImageCrop(filepath=str(cat_image_path), x=0, y=0, width=width, height=height)
        crop_embeddings = mobileclip.embed_image_crops([full_crop])
        image_embeddings = mobileclip.embed_images([str(cat_image_path)])

        assert crop_embeddings.shape == (1, 512)
        # A crop covering the entire image is preprocessed and encoded identically
        # to the full image, so the embeddings must match.
        assert np.allclose(crop_embeddings[0], image_embeddings[0], atol=1e-4)

    def test_embed_pil_images__empty_input(self) -> None:
        mobileclip = MobileCLIPEmbeddingGenerator()
        embeddings = mobileclip.embed_pil_images([])

        assert embeddings.shape == (0, 512)

    def test_embed_pil_images__matches_embed_images(self) -> None:
        mobileclip = MobileCLIPEmbeddingGenerator()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        with Image.open(cat_image_path) as image:
            cat_pil_image = image.convert("RGB")

        pil_embeddings = mobileclip.embed_pil_images([cat_pil_image])
        image_embeddings = mobileclip.embed_images([str(cat_image_path)])

        assert pil_embeddings.shape == (1, 512)
        # An in-memory PIL image is preprocessed and encoded identically to the same
        # image loaded from disk, so the embeddings must match.
        assert np.allclose(pil_embeddings[0], image_embeddings[0], atol=1e-4)

    def test_classification(self) -> None:
        """End-to-end test for embedding consistency.

        Embed texts "a cat", "a dog" and "a tiger". Compare with
        "cat.jpg" image embedding using cosine distance.
        Pick a classification with softmax.
        """
        mobileclip = MobileCLIPEmbeddingGenerator()

        # Embed texts.
        text_emb = torch.tensor(
            [
                mobileclip.embed_text("a cat"),
                mobileclip.embed_text("a dog"),
                mobileclip.embed_text("a tiger"),
            ]
        )
        text_emb /= text_emb.norm(dim=-1, keepdim=True)

        # Embed image.
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        cat_image_emb = torch.tensor(mobileclip.embed_images([str(cat_image_path)])[0])
        cat_image_emb /= cat_image_emb.norm(dim=-1, keepdim=True)

        # Compute softmax similarity as in ml-mobileclip repo example.
        text_probs = (100.0 * cat_image_emb @ text_emb.T).softmax(dim=-1)
        assert np.isclose(text_probs[0], 1.0, atol=1e-3)
        assert np.isclose(text_probs[1], 0.0, atol=1e-3)
        assert np.isclose(text_probs[2], 0.0, atol=1e-3)
