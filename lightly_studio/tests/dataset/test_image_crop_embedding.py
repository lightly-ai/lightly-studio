from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image

from lightly_studio.dataset import image_crop_embedding
from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.dataset.image_embedding import EmbeddingContext


def test_embed_image_crops_batched__empty_input_returns_empty_array() -> None:
    embeddings = image_crop_embedding.embed_image_crops_batched(
        image_crops=[],
        context=EmbeddingContext(
            embedding_dimension=4,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=lambda images_tensor: images_tensor.cpu().numpy(),
        ),
        show_progress=False,
    )

    assert embeddings.shape == (0, 4)


def test_embed_image_crops_batched__preserves_input_order_across_filepaths(
    tmp_path: Path,
) -> None:
    image_a_path = tmp_path / "image_a.png"
    image_b_path = tmp_path / "image_b.png"
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(image_a_path)
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(image_b_path)

    # Crops are interleaved across two files, each with a distinct width. The
    # helper groups crops by filepath before encoding, so the encode order
    # (a, a, b, b) differs from the input order.
    image_crops = [
        ImageCrop(filepath=str(image_a_path), x=0, y=0, width=5, height=10),
        ImageCrop(filepath=str(image_b_path), x=0, y=0, width=6, height=10),
        ImageCrop(filepath=str(image_a_path), x=0, y=0, width=7, height=10),
        ImageCrop(filepath=str(image_b_path), x=0, y=0, width=8, height=10),
    ]
    encode_calls: list[int] = []

    def encode_batch(images_tensor: torch.Tensor) -> NDArray[np.float32]:
        encode_calls.append(images_tensor.size(0))
        # Each preprocessed crop is its width, so the batch is already the
        # expected (batch_size, 1) embedding; encode is the identity here.
        return images_tensor.numpy().astype(np.float32)

    embeddings = image_crop_embedding.embed_image_crops_batched(
        image_crops=image_crops,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=3,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=encode_batch,
        ),
        show_progress=False,
    )

    # Encode order is [a:5, a:7, b:6, b:8]; with max_batch_size=3 the first
    # batch spans both files and the last crop forms a partial final batch.
    assert encode_calls == [3, 1]
    assert embeddings.shape == (4, 1)
    # Each embedding equals its crop width, in input order.
    assert embeddings[:, 0].tolist() == [5.0, 6.0, 7.0, 8.0]
