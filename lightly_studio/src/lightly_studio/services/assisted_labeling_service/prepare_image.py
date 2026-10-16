"""Preparation of an image for later preview requests."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.assisted_labeling import PrepareAnnotationRequest
from lightly_studio.services.assisted_labeling_service import (
    get_active_provider,
    load_provider_image,
)


def prepare_image(session: Session, request: PrepareAnnotationRequest) -> None:
    """Lets the active provider prepare the image, for example by uploading it.

    Raises:
        NotFoundError: If the collection has no image with the sample ID.
        ProviderUnavailableError: If the active provider is not usable.
        ProviderError: If the preparation fails.
    """
    provider = get_active_provider.get_usable_provider(session=session)
    image = load_provider_image.load_provider_image(
        session=session, collection_id=request.collection_id, sample_id=request.sample_id
    )
    provider.prepare(image=image)
