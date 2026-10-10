"""Creation of provider images from image samples."""

from __future__ import annotations

from functools import partial
from uuid import UUID

import fsspec
from sqlmodel import Session

from lightly_studio.assisted_labeling.provider import ProviderImage
from lightly_studio.errors import NotFoundError
from lightly_studio.resolvers import image_resolver


def load_provider_image(session: Session, collection_id: UUID, sample_id: UUID) -> ProviderImage:
    """Returns the provider image of an image sample.

    The image file is read only when the provider calls `read_bytes`.

    Raises:
        NotFoundError: If the collection has no image with the sample ID.
    """
    image = image_resolver.get_by_id(session=session, sample_id=sample_id)
    if image is None or image.sample.collection_id != collection_id:
        raise NotFoundError(f"Image {sample_id} not found in collection {collection_id}.")
    return ProviderImage(
        sample_id=image.sample_id,
        width=image.width,
        height=image.height,
        file_name=image.file_name,
        read_bytes=partial(_read_file, file_path=image.file_path_abs),
    )


def _read_file(file_path: str) -> bytes:
    """Reads a local or cloud file.

    Raises:
        NotFoundError: If the file cannot be read.
    """
    filesystem, path = fsspec.core.url_to_fs(file_path)
    try:
        return bytes(filesystem.cat_file(path))
    except OSError as exc:
        raise NotFoundError(f"The image file '{file_path}' could not be read.") from exc
