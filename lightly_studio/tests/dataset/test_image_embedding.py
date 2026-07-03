from pathlib import Path
from uuid import uuid4

import numpy as np
import torch
from PIL import Image

from lightly_studio.dataset import image_embedding
from lightly_studio.dataset.image_embedding import EmbeddingContext


def _width_context(embedding_dimension: int, max_batch_size: int) -> EmbeddingContext:
    # preprocess encodes an image as its width, so each embedding equals the
    # source image width and order behaviour is easy to assert.
    return EmbeddingContext(
        embedding_dimension=embedding_dimension,
        max_batch_size=max_batch_size,
        device=torch.device("cpu"),
        preprocess=lambda image: torch.tensor([float(image.size[0])]),
        encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
    )


def test_embed_image_files_batched__empty_input_returns_empty_array() -> None:
    result = image_embedding.embed_image_files_batched(
        keyed_filepaths=[],
        context=_width_context(embedding_dimension=4, max_batch_size=2),
        show_progress=False,
    )

    assert result.embeddings.shape == (0, 4)
    assert result.keys == []


def test_embed_image_files_batched__preserves_input_order(tmp_path: Path) -> None:
    # Each image has a distinct width, so the embeddings must come back in input
    # order across batches, each tagged with its sample id.
    widths = [5, 6, 7]
    keys = [uuid4() for _ in widths]
    keyed_filepaths = []
    for index, width in enumerate(widths):
        path = tmp_path / f"image_{index}.png"
        Image.new("RGB", (width, 10), color=(255, 0, 0)).save(path)
        keyed_filepaths.append((keys[index], str(path)))

    result = image_embedding.embed_image_files_batched(
        keyed_filepaths=keyed_filepaths,
        context=_width_context(embedding_dimension=1, max_batch_size=2),
        show_progress=False,
    )

    assert result.embeddings.shape == (3, 1)
    assert result.keys == keys
    assert result.embeddings[:, 0].tolist() == [float(width) for width in widths]
