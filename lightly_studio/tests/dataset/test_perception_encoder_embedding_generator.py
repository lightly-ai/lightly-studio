from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import torch

from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestPerceptionEncoderEmbeddingGenerator:
    def test_get_embedding_model_input(self) -> None:
        perception_encoder = PerceptionEncoderEmbeddingGenerator()
        collection_id = uuid.uuid4()
        embedding_model_input = perception_encoder.get_embedding_model_input(
            collection_id=collection_id
        )

        assert embedding_model_input.name == "PE-Core-T16-384"
        assert embedding_model_input.embedding_dimension == 512
        assert embedding_model_input.collection_id == collection_id
        assert embedding_model_input.embedding_model_hash != ""

    def test_embed_text(self) -> None:
        text = "a cat"
        perception_encoder = PerceptionEncoderEmbeddingGenerator()
        embedding = perception_encoder.embed_text(text)
        assert len(embedding) == 512

        # Normalize and test a few values.
        embedding_normed = np.array(embedding)
        embedding_normed /= np.linalg.norm(embedding_normed)
        assert np.isclose(embedding_normed[0], -0.0108, atol=1e-4)
        assert np.isclose(embedding_normed[1], -0.0152, atol=1e-4)
        assert np.isclose(embedding_normed[2], -0.0406, atol=1e-4)
        assert np.isclose(embedding_normed[3], -0.0312, atol=1e-4)

    def test_embed_images(self) -> None:
        perception_encoder = PerceptionEncoderEmbeddingGenerator()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        embeddings = perception_encoder.embed_images([str(cat_image_path)])

        assert len(embeddings) == 1
        cat_embedding = embeddings[0]
        assert len(cat_embedding) == 512

        # Normalize and test a few values.
        cat_embedding_normed = np.array(cat_embedding)
        cat_embedding_normed /= np.linalg.norm(cat_embedding_normed)
        assert np.isclose(cat_embedding_normed[0], -0.0012, atol=1e-4)
        assert np.isclose(cat_embedding_normed[1], 0.1103, atol=1e-4)
        assert np.isclose(cat_embedding_normed[2], 0.0307, atol=1e-4)
        assert np.isclose(cat_embedding_normed[3], -0.0493, atol=1e-4)

    def test_embed_videos(self) -> None:
        perception_encoder = PerceptionEncoderEmbeddingGenerator()
        dog_video_path = FIXTURES_DIR / "dog.mp4"

        embeddings = perception_encoder.embed_videos([str(dog_video_path)])

        assert len(embeddings) == 1
        cat_video_embedding = embeddings[0]
        assert len(cat_video_embedding) == 512

        # Normalize and test a few values.
        dog_video_embedding_normed = np.array(cat_video_embedding)
        dog_video_embedding_normed /= np.linalg.norm(dog_video_embedding_normed)
        assert np.isclose(dog_video_embedding_normed[0], 0.028, atol=1e-2)
        assert np.isclose(dog_video_embedding_normed[1], 0.057, atol=1e-2)
        assert np.isclose(dog_video_embedding_normed[2], 0.057, atol=1e-2)
        assert np.isclose(dog_video_embedding_normed[3], -0.077, atol=1e-2)

    def test_classification(self) -> None:
        """End-to-end test for embedding consistency.

        Embed texts "a cat", "a dog" and "a tiger". Compare with
        "cat.jpg" image embedding using cosine distance.
        Pick a classification with softmax.
        """
        perception_encoder = PerceptionEncoderEmbeddingGenerator()

        # Embed texts.
        text_emb = torch.tensor(
            [
                perception_encoder.embed_text("a cat"),
                perception_encoder.embed_text("a dog"),
                perception_encoder.embed_text("a tiger"),
            ]
        )
        text_emb /= text_emb.norm(dim=-1, keepdim=True)

        # Embed image.
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        cat_image_emb = torch.tensor(perception_encoder.embed_images([str(cat_image_path)])[0])
        cat_image_emb /= cat_image_emb.norm(dim=-1, keepdim=True)

        # Compute softmax similarity as in perception_encoder repo example.
        text_probs = (100.0 * cat_image_emb @ text_emb.T).softmax(dim=-1)
        assert np.isclose(text_probs[0], 0.99, atol=1e-2)
        assert np.isclose(text_probs[1], 0.00, atol=1e-2)
        assert np.isclose(text_probs[2], 0.01, atol=1e-2)

    def test_classification_video(self) -> None:
        """End-to-end test for embedding consistency.

        Embed texts "giving a {X} a treat" with X=["dog", "horse", "tiger"]. Compare with
        "dog.mp4" image embedding using cosine distance.
        Pick a classification with softmax.
        """
        perception_encoder = PerceptionEncoderEmbeddingGenerator()

        # Embed texts.
        text_emb = torch.tensor(
            [
                perception_encoder.embed_text("giving a dog a treat"),
                perception_encoder.embed_text("giving a horse a treat"),
                perception_encoder.embed_text("giving a tiger a treat"),
            ]
        )
        text_emb /= text_emb.norm(dim=-1, keepdim=True)

        # Embed Video.
        perception_encoder = PerceptionEncoderEmbeddingGenerator()
        dog_video_path = FIXTURES_DIR / "dog.mp4"

        dog_video_emb = torch.tensor(perception_encoder.embed_videos([str(dog_video_path)])[0])
        dog_video_emb /= dog_video_emb.norm(dim=-1, keepdim=True)

        # Compute softmax similarity as in perception_encoder repo example.
        text_probs = (100.0 * dog_video_emb @ text_emb.T).softmax(dim=-1)
        assert np.isclose(text_probs[0], 0.7, atol=1e-1)
        assert np.isclose(text_probs[1], 0.15, atol=1e-1)
        assert np.isclose(text_probs[2], 0.15, atol=1e-1)
