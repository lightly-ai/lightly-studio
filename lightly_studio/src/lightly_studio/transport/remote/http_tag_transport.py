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

    def get_names_by_sample_ids(self, sample_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
        """Get the tag names of samples. Not supported over HTTP yet."""
        raise NotImplementedError("Getting the tags of samples over HTTP is not supported yet.")

    def add_to_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Add a tag to samples. Create the tag if it does not exist."""
        path = f"/collections/{collection_id}/tags:add"
        # One request without samples still creates the tag.
        for batch in _batches(ids=sample_ids) or [[]]:
            self._send(path=path, tag_name=tag_name, sample_ids=batch)

    def remove_from_samples(
        self, collection_id: UUID, tag_name: str, sample_ids: Sequence[UUID]
    ) -> None:
        """Remove a tag from samples. A tag that does not exist changes nothing."""
        path = f"/collections/{collection_id}/tags:remove"
        for batch in _batches(ids=sample_ids):
            self._send(path=path, tag_name=tag_name, sample_ids=batch)

    def _send(self, path: str, tag_name: str, sample_ids: list[str]) -> None:
        body = {"tag_name": tag_name, "sample_ids": sample_ids}
        http_requests.post(client=self._client, path=path, body=body)


def _batches(ids: Sequence[UUID]) -> list[list[str]]:
    return [
        [str(sample_id) for sample_id in ids[start : start + MAX_SAMPLE_IDS_PER_REQUEST]]
        for start in range(0, len(ids), MAX_SAMPLE_IDS_PER_REQUEST)
    ]
