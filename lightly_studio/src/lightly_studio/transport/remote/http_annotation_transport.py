"""Annotation transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationView
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.annotation.polygon import Polygons
from lightly_studio.models.annotation_label import AnnotationLabelView
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates


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

    def get_by_sample_ids_and_collection(
        self, sample_ids: Sequence[UUID], annotation_collection_id: UUID
    ) -> list[AnnotationView]:
        """Get the annotations of samples in a collection. Not supported over HTTP yet."""
        raise NotImplementedError("Getting annotations over HTTP is not supported yet.")

    def get_covered_sequence_ids(self, annotation_collection_id: UUID) -> list[UUID]:
        """Get the covered sequences. Not supported over HTTP yet."""
        raise NotImplementedError("Finding labeled sequences over HTTP is not supported yet.")

    def create(
        self,
        parent_collection_id: UUID,
        annotations: Sequence[AnnotationCreate],
        collection_name: str | None,
        covered_sample_ids: Sequence[UUID],
    ) -> list[UUID]:
        """Add annotations to samples. Not supported over HTTP yet."""
        raise NotImplementedError("Adding annotations over HTTP is not supported yet.")

    def update_bounding_box(
        self, annotation_id: UUID, bounding_box: BoundingBoxCoordinates
    ) -> None:
        """Replace the bounding box of an annotation. Not supported over HTTP yet."""
        raise NotImplementedError("Updating annotations over HTTP is not supported yet.")

    def update_segmentation_mask(
        self, annotation_id: UUID, segmentation_mask: Sequence[int]
    ) -> None:
        """Replace the segmentation mask of an annotation. Not supported over HTTP yet."""
        raise NotImplementedError("Updating annotations over HTTP is not supported yet.")

    def update_polygons(self, annotation_id: UUID, polygons: Polygons) -> None:
        """Replace the polygons of an annotation. Not supported over HTTP yet."""
        raise NotImplementedError("Updating annotations over HTTP is not supported yet.")

    def delete(self, annotation_ids: Sequence[UUID]) -> None:
        """Delete annotations by ID. Not supported over HTTP yet."""
        raise NotImplementedError("Deleting annotations over HTTP is not supported yet.")

    def delete_empty_object_tracks(self, object_track_ids: Sequence[UUID]) -> int:
        """Delete empty object tracks. Not supported over HTTP yet."""
        raise NotImplementedError("Object tracks over HTTP are not supported yet.")

    def get_free_object_track_numbers(self, dataset_id: UUID, count: int) -> list[int]:
        """Get free object track numbers. Not supported over HTTP yet."""
        raise NotImplementedError("Object tracks over HTTP are not supported yet.")

    def create_object_tracks(self, tracks: Sequence[ObjectTrackCreate]) -> list[UUID]:
        """Add object tracks. Not supported over HTTP yet."""
        raise NotImplementedError("Object tracks over HTTP are not supported yet.")
