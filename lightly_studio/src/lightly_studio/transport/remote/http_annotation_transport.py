"""Annotation transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationView
from lightly_studio.models.annotation_label import AnnotationLabelView


class HttpAnnotationTransport:
    """Implements `AnnotationTransport` over HTTP. The v1 API has no annotation routes yet."""

    def __init__(self, client: httpx.Client) -> None:
        """Create the transport with an HTTP client for the Studio backend."""
        self._client = client

    def get_or_create_labels(
        self, dataset_id: UUID, label_names: Sequence[str]
    ) -> list[AnnotationLabelView]:
        """Get annotation classes by name. Not supported over HTTP yet."""
        raise NotImplementedError("Annotation classes over HTTP are not supported yet.")

    def get_by_sample_ids(self, sample_ids: Sequence[UUID]) -> list[AnnotationView]:
        """Get the annotations of samples. Not supported over HTTP yet."""
        raise NotImplementedError("Getting annotations over HTTP is not supported yet.")

    def create(
        self,
        parent_collection_id: UUID,
        annotations: Sequence[AnnotationCreate],
        collection_name: str | None,
        covered_sample_ids: Sequence[UUID],
    ) -> list[UUID]:
        """Add annotations to samples. Not supported over HTTP yet."""
        raise NotImplementedError("Adding annotations over HTTP is not supported yet.")

    def delete(self, annotation_ids: Sequence[UUID]) -> None:
        """Delete annotations by ID. Not supported over HTTP yet."""
        raise NotImplementedError("Deleting annotations over HTTP is not supported yet.")
