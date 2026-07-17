import time
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

from lightly_studio.dataset import image_embedding
from lightly_studio.dataset.image_embedding import EmbeddingContext


def test_embed_image_files_batched__empty_input_returns_empty_array() -> None:
    embeddings = image_embedding.embed_image_files_batched(
        filepaths=[],
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


def test_embed_image_files_batched__preserves_input_order(tmp_path: Path) -> None:
    # Each image has a distinct width, and preprocess encodes an image as its
    # width, so the embeddings must come back in input order across batches.
    widths = [5, 6, 7]
    filepaths = []
    for index, width in enumerate(widths):
        path = tmp_path / f"image_{index}.png"
        Image.new("RGB", (width, 10), color=(255, 0, 0)).save(path)
        filepaths.append(str(path))

    embeddings = image_embedding.embed_image_files_batched(
        filepaths=filepaths,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
        ),
        show_progress=False,
    )

    assert embeddings.shape == (3, 1)
    assert embeddings[:, 0].tolist() == [float(width) for width in widths]


def test_embed_image_files_batched__preserves_order_despite_out_of_order_preprocess(
    tmp_path: Path,
) -> None:
    # The first image preprocesses slowest, so with concurrent preprocessing it finishes
    # last and completion order differs from input order; this guards that embeddings still
    # come back aligned to input order. The delay is a short, bounded sleep on the first
    # image only, so the test stays fast and still passes (in order) when preprocessing
    # happens to run single-threaded.
    widths = [5, 6, 7, 8]
    filepaths = []
    for index, width in enumerate(widths):
        path = tmp_path / f"image_{index}.png"
        Image.new("RGB", (width, 10), color=(255, 0, 0)).save(path)
        filepaths.append(str(path))

    def preprocess(image: Image.Image) -> torch.Tensor:
        if image.size[0] == widths[0]:
            time.sleep(0.1)
        return torch.tensor([float(image.size[0])])

    embeddings = image_embedding.embed_image_files_batched(
        filepaths=filepaths,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=preprocess,
            encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
        ),
        show_progress=False,
    )

    assert embeddings[:, 0].tolist() == [float(width) for width in widths]


def test_embed_image_files_batched__propagates_preprocess_error(tmp_path: Path) -> None:
    filepaths = []
    for index in range(3):
        path = tmp_path / f"image_{index}.png"
        Image.new("RGB", (10, 10), color=(255, 0, 0)).save(path)
        filepaths.append(str(path))

    def preprocess(_image: Image.Image) -> torch.Tensor:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        image_embedding.embed_image_files_batched(
            filepaths=filepaths,
            context=EmbeddingContext(
                embedding_dimension=1,
                max_batch_size=2,
                device=torch.device("cpu"),
                preprocess=preprocess,
                encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
            ),
            show_progress=False,
        )


def test_embed_pil_images_batched__empty_input_returns_empty_array() -> None:
    embeddings = image_embedding.embed_pil_images_batched(
        images=[],
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


def test_embed_pil_images_batched__preserves_input_order() -> None:
    widths = [5, 6, 7]
    images = [Image.new("RGB", (width, 10), color=(255, 0, 0)) for width in widths]

    embeddings = image_embedding.embed_pil_images_batched(
        images=images,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
        ),
        show_progress=False,
    )

    assert embeddings.shape == (3, 1)
    assert embeddings[:, 0].tolist() == [float(width) for width in widths]
