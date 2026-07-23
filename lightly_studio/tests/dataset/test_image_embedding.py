import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image

if TYPE_CHECKING:
    import torch

torch = pytest.importorskip("torch")

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError  # noqa: E402
from lightly_studio.dataset import image_embedding  # noqa: E402
from lightly_studio.dataset.image_embedding import EmbeddingContext  # noqa: E402


def test_embed_image_files_batched__empty_input_returns_empty_array() -> None:
    result = image_embedding.embed_image_files_batched(
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

    assert result.embeddings.shape == (0, 4)
    assert result.kept_indices == []


def test_embed_image_files_batched__preserves_input_order(tmp_path: Path) -> None:
    # Each image has a distinct width, and preprocess encodes an image as its
    # width, so the embeddings must come back in input order across batches.
    widths = [5, 6, 7]
    filepaths = _write_images(tmp_path=tmp_path, widths=widths)

    result = image_embedding.embed_image_files_batched(
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

    assert result.embeddings.shape == (3, 1)
    assert result.kept_indices == [0, 1, 2]
    assert result.embeddings[:, 0].tolist() == [float(width) for width in widths]


def test_embed_image_files_batched__preserves_order_despite_out_of_order_preprocess(
    tmp_path: Path,
) -> None:
    # The first image preprocesses slowest, so with concurrent preprocessing it finishes
    # last and completion order differs from input order; this guards that embeddings still
    # come back aligned to input order. The delay is a short, bounded sleep on the first
    # image only, so the test stays fast and still passes (in order) when preprocessing
    # happens to run single-threaded.
    widths = [5, 6, 7, 8]
    filepaths = _write_images(tmp_path=tmp_path, widths=widths)

    def preprocess(image: Image.Image) -> torch.Tensor:
        if image.size[0] == widths[0]:
            time.sleep(0.1)
        return torch.tensor([float(image.size[0])])

    result = image_embedding.embed_image_files_batched(
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

    assert result.embeddings[:, 0].tolist() == [float(width) for width in widths]


def test_embed_image_files_batched__skips_broken_files(tmp_path: Path) -> None:
    # Broken files are skipped per-item: the embeddings cover only the readable files and
    # kept_indices maps each row back to its input position, so callers stay in sync.
    widths = [5, 6, 7, 8]
    valid_filepaths = _write_images(tmp_path=tmp_path, widths=widths)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a valid image")
    missing = tmp_path / "missing.png"
    # Interleave broken/missing files with readable ones at positions 1 and 3.
    filepaths = [
        valid_filepaths[0],
        str(broken),
        valid_filepaths[1],
        str(missing),
        valid_filepaths[2],
        valid_filepaths[3],
    ]

    result = image_embedding.embed_image_files_batched(
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

    assert result.kept_indices == [0, 2, 4, 5]
    assert result.embeddings[:, 0].tolist() == [float(width) for width in widths]


def test_embed_image_files_batched__raises_when_all_files_broken(tmp_path: Path) -> None:
    broken_paths = []
    for index in range(3):
        path = tmp_path / f"broken_{index}.png"
        path.write_bytes(b"not a valid image")
        broken_paths.append(str(path))

    with pytest.raises(AllInputFilesFailedError):
        image_embedding.embed_image_files_batched(
            filepaths=broken_paths,
            context=EmbeddingContext(
                embedding_dimension=1,
                max_batch_size=2,
                device=torch.device("cpu"),
                preprocess=lambda image: torch.tensor([float(image.size[0])]),
                encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
            ),
            show_progress=False,
        )


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


def _write_images(tmp_path: Path, widths: list[int]) -> list[str]:
    """Write one RGB image per width and return their file paths, in order."""
    filepaths = []
    for index, width in enumerate(widths):
        path = tmp_path / f"image_{index}.png"
        Image.new("RGB", (width, 10), color=(255, 0, 0)).save(path)
        filepaths.append(str(path))
    return filepaths
