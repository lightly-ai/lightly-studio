"""Tag transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from lightly_studio.models.tag import MAX_SAMPLE_IDS_PER_REQUEST, TagView
from lightly_studio.transport.remote import http_requests


class HttpTagTransport:
    """Implements `TagTransport` over HTTP. Writes send one request per batch of samples."""

    def __init__(self, client: httpx.Client) -> None:
        """Create the transport with an HTTP client for the Studio backend."""
        self._client = client

    def get_by_name(self, collection_id: UUID, tag_name: str) -> TagView | None:
        """Get a tag of a collection by name, or None if it does not exist."""
        body = http_requests.get(
            client=self._client,
            path=f"/collections/{collection_id}/tags",
            params={"name": tag_name},
        )
        return None if body is None else TagView.model_validate(body)

    def add_to_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Add a tag to samples. Create the tag if it does not exist."""
        self._send(path=f"/collections/{collection_id}/tags:add", tag_name=tag_name, ids=sample_ids)

    def remove_from_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Remove a tag from samples. A tag that does not exist changes nothing."""
        self._send(
            path=f"/collections/{collection_id}/tags:remove", tag_name=tag_name, ids=sample_ids
        )

    def _send(self, path: str, tag_name: str, ids: Sequence[UUID]) -> None:
        # One request without samples still creates the tag.
        for start in range(0, max(len(ids), 1), MAX_SAMPLE_IDS_PER_REQUEST):
            batch = [
                str(sample_id) for sample_id in ids[start : start + MAX_SAMPLE_IDS_PER_REQUEST]
            ]
            body = {"tag_name": tag_name, "sample_ids": batch}
            http_requests.post(client=self._client, path=path, body=body)
