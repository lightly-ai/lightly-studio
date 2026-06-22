from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image

from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.dataset.image_crop_embedding import embed_image_crops_batched


def test_embed_image_crops_batched__empty_input_returns_empty_array() -> None:
    embeddings = embed_image_crops_batched(
        [],
        embedding_dimension=4,
        max_batch_size=2,
        device=torch.device("cpu"),
        preprocess=lambda image: torch.tensor([float(image.size[0])]),
        encode_batch=lambda images_tensor: images_tensor.numpy(),
        show_progress=False,
    )

    assert embeddings.shape == (0, 4)


def test_embed_image_crops_batched__preserves_input_order(tmp_path: Path) -> None:
    image_path = tmp_path / "image.png"
    Image.new("RGB", (20, 10), color=(255, 0, 0)).save(image_path)

    image_crops = [
        ImageCrop(filepath=str(image_path), x=0, y=0, width=5, height=5),
        ImageCrop(filepath=str(image_path), x=5, y=0, width=5, height=5),
        ImageCrop(filepath=str(image_path), x=10, y=0, width=5, height=5),
    ]
    encode_calls: list[int] = []

    def encode_batch(images_tensor: torch.Tensor) -> NDArray[np.float32]:
        encode_calls.append(images_tensor.size(0))
        return np.column_stack(
            [
                images_tensor[:, 0].numpy(),
                images_tensor[:, 0].numpy() + 1.0,
            ]
        ).astype(np.float32)

    embeddings = embed_image_crops_batched(
        image_crops,
        embedding_dimension=2,
        max_batch_size=2,
        device=torch.device("cpu"),
        preprocess=lambda image: torch.tensor([float(image.size[0])]),
        encode_batch=encode_batch,
        show_progress=False,
    )

    assert encode_calls == [2, 1]
    assert embeddings.shape == (3, 2)
    assert embeddings[0, 0] == 5.0
    assert embeddings[1, 0] == 5.0
    assert embeddings[2, 0] == 5.0
