from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.embed.perception_encoder_embedder import (
    MODEL_NAME,
    PerceptionEncoderEmbedder,
)
from lightly_studio.embed.types import ImageCrop

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestPerceptionEncoderEmbedder:
    def test_embedding_space_spec(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        space_spec = perception_encoder.embedding_space_spec()

        assert space_spec.dimension == 512
        assert space_spec.space_key == MODEL_NAME

    def test_embed_text(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        result = perception_encoder.embed_text(texts=["a cat"])

        assert result.kept_indices == [0]
        assert result.embeddings.shape == (1, 512)

        # Normalize and test a few values.
        embedding_normed = result.embeddings[0]
        embedding_normed /= np.linalg.norm(embedding_normed)
        assert np.isclose(embedding_normed[0], -0.0108, atol=1e-4)
        assert np.isclose(embedding_normed[1], -0.0152, atol=1e-4)
        assert np.isclose(embedding_normed[2], -0.0406, atol=1e-4)
        assert np.isclose(embedding_normed[3], -0.0312, atol=1e-4)

    def test_embed_text__empty_input(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()

        result = perception_encoder.embed_text(texts=[])

        assert result.embeddings.shape == (0, 512)
        assert result.embeddings.dtype == np.float32
        assert result.kept_indices == []

    def test_embed_images(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        embeddings = perception_encoder.embed_images([str(cat_image_path)]).embeddings

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

    def test_embed_image_crops__empty_input(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        result = perception_encoder.embed_image_crops(crops=[])

        assert result.embeddings.shape == (0, 512)
        assert result.kept_indices == []

    def test_embed_image_crops__full_image_crop_matches_embed_images(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        with Image.open(cat_image_path) as image:
            width, height = image.size

        full_crop = ImageCrop(filepath=str(cat_image_path), x=0, y=0, width=width, height=height)
        crop_result = perception_encoder.embed_image_crops(crops=[full_crop])
        image_result = perception_encoder.embed_images(paths=[str(cat_image_path)])

        assert crop_result.embeddings.shape == (1, 512)
        assert crop_result.kept_indices == [0]
        # A crop covering the entire image is preprocessed and encoded identically
        # to the full image, so the embeddings must match.
        assert np.allclose(crop_result.embeddings[0], image_result.embeddings[0], atol=1e-4)

    def test_embed_frames__empty_input(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        result = perception_encoder.embed_frames(frames=[])

        assert result.embeddings.shape == (0, 512)
        assert result.kept_indices == []

    def test_embed_frames__matches_embed_images(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        with Image.open(cat_image_path) as image:
            cat_pil_image = image.convert("RGB")

        frame_result = perception_encoder.embed_frames(frames=[cat_pil_image])
        image_result = perception_encoder.embed_images(paths=[str(cat_image_path)])

        assert frame_result.embeddings.shape == (1, 512)
        assert frame_result.kept_indices == [0]
        # An in-memory PIL image is preprocessed and encoded identically to the same
        # image loaded from disk, so the embeddings must match.
        assert np.allclose(frame_result.embeddings[0], image_result.embeddings[0], atol=1e-4)

    def test_embed_videos(self) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        dog_video_path = FIXTURES_DIR / "dog.mp4"

        result = perception_encoder.embed_videos([str(dog_video_path)])
        embeddings = result.embeddings

        assert result.kept_indices == [0]
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

    def test_embed_videos__skips_broken_and_missing(self, tmp_path: Path) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        dog_video_path = FIXTURES_DIR / "dog.mp4"
        broken_path = tmp_path / "broken.mp4"
        broken_path.write_bytes(b"not a valid video")
        missing_path = tmp_path / "missing.mp4"

        # Interleave the broken/missing files with the readable one.
        filepaths = [
            str(broken_path),
            str(dog_video_path),
            str(missing_path),
            str(dog_video_path),
        ]

        result = perception_encoder.embed_videos(filepaths)

        assert result.kept_indices == [1, 3]
        assert result.embeddings.shape == (2, 512)
        # The two kept rows embed the same video, so they must match.
        assert np.allclose(result.embeddings[0], result.embeddings[1])

    def test_embed_videos__raises_when_all_files_broken(self, tmp_path: Path) -> None:
        perception_encoder = PerceptionEncoderEmbedder()
        broken_path = tmp_path / "broken.mp4"
        broken_path.write_bytes(b"not a valid video")

        with pytest.raises(AllInputFilesFailedError):
            perception_encoder.embed_videos([str(broken_path), str(broken_path)])

    def test_classification(self) -> None:
        """End-to-end test for embedding consistency.

        Embed texts "a cat", "a dog" and "a tiger". Compare with
        "cat.jpg" image embedding using cosine distance.
        Pick a classification with softmax.
        """
        perception_encoder = PerceptionEncoderEmbedder()

        # Embed texts.
        text_emb = torch.from_numpy(
            perception_encoder.embed_text(texts=["a cat", "a dog", "a tiger"]).embeddings
        )
        text_emb /= text_emb.norm(dim=-1, keepdim=True)

        # Embed image.
        cat_image_path = FIXTURES_DIR / "cat.jpg"
        cat_image_emb = torch.tensor(
            perception_encoder.embed_images([str(cat_image_path)]).embeddings[0]
        )
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
        perception_encoder = PerceptionEncoderEmbedder()

        # Embed texts.
        text_emb = torch.from_numpy(
            perception_encoder.embed_text(
                texts=[
                    "giving a dog a treat",
                    "giving a horse a treat",
                    "giving a tiger a treat",
                ]
            ).embeddings
        )
        text_emb /= text_emb.norm(dim=-1, keepdim=True)

        # Embed Video.
        perception_encoder = PerceptionEncoderEmbedder()
        dog_video_path = FIXTURES_DIR / "dog.mp4"

        dog_video_emb = torch.tensor(
            perception_encoder.embed_videos([str(dog_video_path)]).embeddings[0]
        )
        dog_video_emb /= dog_video_emb.norm(dim=-1, keepdim=True)

        # Compute softmax similarity as in perception_encoder repo example.
        text_probs = (100.0 * dog_video_emb @ text_emb.T).softmax(dim=-1)
        assert np.isclose(text_probs[0], 0.7, atol=1e-1)
        assert np.isclose(text_probs[1], 0.15, atol=1e-1)
        assert np.isclose(text_probs[2], 0.15, atol=1e-1)
