from __future__ import annotations

import io
import threading
import time
from pathlib import Path

import fsspec
import numpy as np
import pytest
import torch
from numpy.typing import NDArray
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.dataset import image_crop_embedding
from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.dataset.image_embedding import EmbeddingContext
from lightly_studio.utils import executor


def test_embed_image_crops_batched__empty_input_returns_empty_array() -> None:
    result = image_crop_embedding.embed_image_crops_batched(
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

    assert result.embeddings.shape == (0, 4)
    assert result.kept_indices == []


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

    result = image_crop_embedding.embed_image_crops_batched(
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
    assert result.embeddings.shape == (4, 1)
    assert result.kept_indices == [0, 1, 2, 3]
    # Each embedding equals its crop width, in input order.
    assert result.embeddings[:, 0].tolist() == [5.0, 6.0, 7.0, 8.0]


def test_embed_image_crops_batched__splits_many_crops_into_embedding_batches(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "image.png"
    Image.new("RGB", (100, 100)).save(image_path)
    image_crops = [
        ImageCrop(filepath=str(image_path), x=0, y=0, width=width, height=10)
        for width in range(5, 10)
    ]
    encode_calls: list[int] = []

    def encode_batch(images_tensor: torch.Tensor) -> NDArray[np.float32]:
        encode_calls.append(images_tensor.size(0))
        return images_tensor.numpy().astype(np.float32)

    result = image_crop_embedding.embed_image_crops_batched(
        image_crops=image_crops,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=encode_batch,
        ),
        show_progress=False,
    )

    assert encode_calls == [2, 2, 1]
    assert result.embeddings[:, 0].tolist() == [5.0, 6.0, 7.0, 8.0, 9.0]


def test_embed_image_crops_batched__parallelizes_source_image_loading(
    mocker: MockerFixture,
) -> None:
    image_buffer = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image_buffer, format="PNG")
    image_bytes = image_buffer.getvalue()
    in_flight = 0
    peak_in_flight = 0
    lock = threading.Lock()
    caller_thread = threading.get_ident()
    preprocess_threads: list[int] = []

    class RemoteFile(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal in_flight, peak_in_flight
            with lock:
                in_flight += 1
                peak_in_flight = max(peak_in_flight, in_flight)
            time.sleep(0.02)
            contents = super().read(size)
            with lock:
                in_flight -= 1
            return contents

    open_file = mocker.patch.object(
        fsspec,
        "open",
        side_effect=lambda _path, _mode: RemoteFile(image_bytes),
    )
    mocker.patch.object(executor, "get_media_worker_count", return_value=3)
    paths = [f"s3://bucket/image_{index}.png" for index in range(4)]
    image_crops = [ImageCrop(filepath=path, x=0, y=0, width=5, height=10) for path in paths]
    image_crops.append(ImageCrop(filepath=paths[0], x=0, y=0, width=7, height=10))

    def preprocess(image: Image.Image) -> torch.Tensor:
        preprocess_threads.append(threading.get_ident())
        return torch.tensor([float(image.size[0])])

    result = image_crop_embedding.embed_image_crops_batched(
        image_crops=image_crops,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=preprocess,
            encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
        ),
        show_progress=False,
    )

    assert 1 < peak_in_flight <= 3
    assert open_file.call_count == len(paths)
    assert set(preprocess_threads) == {caller_thread}
    assert result.kept_indices == list(range(len(image_crops)))
    assert result.embeddings[:, 0].tolist() == [5.0, 5.0, 5.0, 5.0, 7.0]


def test_embed_image_crops_batched__skips_broken_file(tmp_path: Path) -> None:
    # Crops of a broken/missing source file are skipped per-file: the embeddings cover
    # only crops of readable files and kept_indices maps each row back to its input
    # position, so callers stay in sync.
    good_path = tmp_path / "good.png"
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(good_path)
    broken_path = tmp_path / "broken.png"
    broken_path.write_bytes(b"not a valid image")
    missing_path = tmp_path / "missing.png"

    # Interleave crops of the broken/missing files with crops of the good file.
    image_crops = [
        ImageCrop(filepath=str(broken_path), x=0, y=0, width=4, height=10),
        ImageCrop(filepath=str(good_path), x=0, y=0, width=5, height=10),
        ImageCrop(filepath=str(missing_path), x=0, y=0, width=6, height=10),
        ImageCrop(filepath=str(good_path), x=0, y=0, width=7, height=10),
    ]

    result = image_crop_embedding.embed_image_crops_batched(
        image_crops=image_crops,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
        ),
        show_progress=False,
    )

    assert result.kept_indices == [1, 3]
    assert result.embeddings[:, 0].tolist() == [5.0, 7.0]


def test_embed_image_crops_batched__skips_decompression_bomb_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good_path = tmp_path / "good.png"
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(good_path)  # 10_000 pixels
    bomb_path = tmp_path / "bomb.png"
    Image.new("RGB", (300, 300), color=(0, 255, 0)).save(bomb_path)  # 90_000 pixels
    # Limit sits between the two images so only the bomb exceeds it.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 20_000)

    image_crops = [
        ImageCrop(filepath=str(bomb_path), x=0, y=0, width=4, height=10),
        ImageCrop(filepath=str(good_path), x=0, y=0, width=5, height=10),
        ImageCrop(filepath=str(good_path), x=0, y=0, width=7, height=10),
    ]

    result = image_crop_embedding.embed_image_crops_batched(
        image_crops=image_crops,
        context=EmbeddingContext(
            embedding_dimension=1,
            max_batch_size=2,
            device=torch.device("cpu"),
            preprocess=lambda image: torch.tensor([float(image.size[0])]),
            encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
        ),
        show_progress=False,
    )

    assert result.kept_indices == [1, 2]
    assert result.embeddings[:, 0].tolist() == [5.0, 7.0]


def test_embed_image_crops_batched__raises_when_all_files_broken(tmp_path: Path) -> None:
    broken_path = tmp_path / "broken.png"
    broken_path.write_bytes(b"not a valid image")
    image_crops = [
        ImageCrop(filepath=str(broken_path), x=0, y=0, width=4, height=10),
        ImageCrop(filepath=str(broken_path), x=0, y=0, width=5, height=10),
    ]

    with pytest.raises(AllInputFilesFailedError):
        image_crop_embedding.embed_image_crops_batched(
            image_crops=image_crops,
            context=EmbeddingContext(
                embedding_dimension=1,
                max_batch_size=2,
                device=torch.device("cpu"),
                preprocess=lambda image: torch.tensor([float(image.size[0])]),
                encode_batch=lambda images_tensor: images_tensor.numpy().astype(np.float32),
            ),
            show_progress=False,
        )
