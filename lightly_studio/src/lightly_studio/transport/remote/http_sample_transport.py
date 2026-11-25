"""Sample transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from lightly_studio.models.sample import SampleView
from lightly_studio.models.sample_query import SamplePage, SampleQueryRequest
from lightly_studio.transport.remote import http_requests


class HttpSampleTransport:
    """Implements `SampleTransport` over HTTP."""

    def __init__(self, client: httpx.Client) -> None:
        """Create the transport with an HTTP client for the Studio backend."""
        self._client = client

    def get_by_ids(self, sample_ids: Sequence[UUID]) -> list[SampleView]:
        """Get samples by ID. Not supported over HTTP yet."""
        raise NotImplementedError("Getting samples by ID over HTTP is not supported yet.")

    def query(self, collection_id: UUID, request: SampleQueryRequest) -> SamplePage:
        """Get one page of the image samples of a collection that match a request."""
        body = http_requests.post(
            client=self._client,
            path=f"/collections/{collection_id}/samples:query",
            body=request.model_dump(mode="json"),
        )
        return SamplePage.model_validate(body)

    def get_image_ids_by_paths(
        self, collection_id: UUID, file_paths: Sequence[str]
    ) -> dict[str, UUID]:
        """Get the sample IDs of images by path. Not supported over HTTP yet."""
        raise NotImplementedError("Getting images by path over HTTP is not supported yet.")

    def get_video_ids_by_stems(self, collection_id: UUID) -> dict[str, UUID]:
        """Get the sample IDs of videos by stem. Not supported over HTTP yet."""
        raise NotImplementedError("Getting videos by stem over HTTP is not supported yet.")
