"""Utilities for importing images from Hugging Face datasets."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from PIL import Image

from lightly_studio.type_definitions import PathLike


def materialize_images(
    hugging_face_dataset: Iterable[Mapping[str, Any]],
    images_path: PathLike,
    image_column: str,
    limit: int | None,
) -> list[str]:
    """Save a Hugging Face dataset's decoded images to a local directory.

    Args:
        hugging_face_dataset: Hugging Face dataset yielding mappings of column names to values.
        images_path: Directory in which to save the images.
        image_column: Name of the column containing decoded Pillow images.
        limit: Maximum number of images to save. If None, save all images.

    Returns:
        Paths of the saved images.

    Raises:
        ValueError: If a row has no image column or its value is not a Pillow image.
    """
    output_path = Path(images_path).expanduser().absolute()
    output_path.mkdir(parents=True, exist_ok=True)
    image_paths: list[str] = []
    for index, row in enumerate(hugging_face_dataset):
        if limit is not None and index >= limit:
            break
        image = _get_image(row=row, image_column=image_column, index=index)
        image_path = output_path / _image_filename(image=image, index=index)
        _save_image(image=image, image_path=image_path)
        image_paths.append(str(image_path))
    return image_paths


def _save_image(image: Image.Image, image_path: Path) -> None:
    """Save an image to disk, converting modes unsupported by the target format.

    Some Hugging Face datasets yield images in modes (e.g. CMYK) that Pillow
    cannot write to formats like PNG. Convert such images to RGB before saving.
    """
    if image.mode not in ("RGB", "RGBA", "L", "LA", "P", "1", "I", "F"):
        image = image.convert("RGB")
    image.save(image_path)


def _get_image(row: Mapping[str, Any], image_column: str, index: int) -> Image.Image:
    if image_column not in row:
        raise ValueError(f"Hugging Face dataset row {index} has no '{image_column}' column.")
    image = row[image_column]
    if not isinstance(image, Image.Image):
        raise ValueError(
            f"Hugging Face dataset row {index} column '{image_column}' must contain a Pillow image."
        )
    return image


def _image_filename(image: Image.Image, index: int) -> str:
    source_name = Path(getattr(image, "filename", "")).name
    digest = _image_digest(image)
    if source_name:
        return f"{index:08d}_{digest}_{source_name}"
    extension = Image.registered_extensions()
    format_to_extension = {image_format: ext for ext, image_format in extension.items()}
    image_extension = format_to_extension.get(image.format or "", ".png")
    return f"{index:08d}_{digest}_image{image_extension}"


def _image_digest(image: Image.Image) -> str:
    digest = hashlib.sha256()
    digest.update(image.mode.encode())
    digest.update(str(image.size).encode())
    digest.update(image.tobytes())
    return digest.hexdigest()[:16]
