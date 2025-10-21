from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lightly_studio.dataset.loader import DatasetLoader


def test_from_directory(
    patch_loader: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # Create a temporary directory for the dataset.
    dataset_path = tmp_path / "my_dataset"
    dataset_path.mkdir(parents=True, exist_ok=True)

    # Create sample images in the dataset directory.
    _create_sample_images(
        [
            dataset_path / "im1.jpg",
            dataset_path / "im2.png",
            dataset_path / "im3.BMP",
            dataset_path / "subfolder" / "im4.gif",
        ]
    )

    # Load the dataset from the path.
    loader = DatasetLoader()
    dataset = loader.from_directory(
        dataset_name="test_dataset",
        img_dir=str(dataset_path),
    )

    # Check the loaded sample count.
    samples = dataset.get_samples()
    assert len(samples) == 4
    assert {s.file_name for s in samples} == {"im1.jpg", "im2.png", "im3.BMP", "im4.gif"}


def test_from_directory__invalid_dir(
    patch_loader: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # Create a temporary file.
    file = tmp_path / "file.txt"
    file.touch()

    # Load the dataset from a file.
    loader = DatasetLoader()
    with pytest.raises(ValueError, match="File is not an image:.*file.txt"):
        loader.from_directory(
            dataset_name="test_dataset",
            img_dir=str(file),
        )

    # Load the dataset from a nonexistent directory.
    loader = DatasetLoader()
    with pytest.raises(ValueError, match="Path does not exist: nonexistent_dir"):
        loader.from_directory(
            dataset_name="test_dataset_2",
            img_dir="nonexistent_dir",
        )


def test_from_directory__non_recursive(
    patch_loader: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # Create a temporary directory for the dataset.
    dataset_path = tmp_path / "my_dataset"
    dataset_path.mkdir(parents=True, exist_ok=True)

    # Create sample images in the dataset directory.
    _create_sample_images(
        [
            dataset_path / "im1.jpg",
            dataset_path / "im2.png",
            dataset_path / "im3.BMP",
            dataset_path / "subfolder" / "im4.gif",
        ]
    )

    # Load the dataset from the path.
    loader = DatasetLoader()
    dataset = loader.from_directory(
        dataset_name="test_dataset",
        img_dir=str(dataset_path / "*.*"),
    )

    # Check the loaded sample count.
    samples = dataset.get_samples()
    assert len(samples) == 3


def test_from_directory__extensions(
    patch_loader: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # Create a temporary directory for the dataset.
    dataset_path = tmp_path / "my_dataset"
    dataset_path.mkdir(parents=True, exist_ok=True)

    # Create sample images in the dataset directory.
    _create_sample_images(
        [
            dataset_path / "im1.jpg",
            dataset_path / "im2.png",
            dataset_path / "subfolder" / "im2.jpg",
            dataset_path / "im4.bmp",
        ]
    )

    # Load the dataset from the path.
    loader = DatasetLoader()
    dataset_allowed_extensions = loader.from_directory(
        dataset_name="test_dataset_allowed_extensions",
        img_dir=str(dataset_path),
        allowed_extensions=[".png", ".jpg"],
    )

    # Check the loaded sample count.
    samples_allowed_extensions = dataset_allowed_extensions.get_samples()
    assert len(samples_allowed_extensions) == 3


def test_from_directory__corrupt_file(
    patch_loader: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    # Create a temporary directory for the dataset.
    dataset_path = tmp_path / "my_dataset"
    dataset_path.mkdir(parents=True, exist_ok=True)

    # Create sample images in the dataset directory.
    image_path = dataset_path / "im1.jpg"
    image_path.write_text("corrupt data")

    # Load the dataset from the path.
    loader = DatasetLoader()
    dataset = loader.from_directory(
        dataset_name="test_dataset",
        img_dir=str(dataset_path),
    )

    # Check the loaded sample count.
    samples = dataset.get_samples()
    assert len(samples) == 0


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)
