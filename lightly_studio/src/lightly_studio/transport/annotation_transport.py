"""Transport protocol for annotations and annotation labels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationView
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.annotation.polygon import Polygons
from lightly_studio.models.annotation_label import AnnotationLabelView
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates


class AnnotationTransport(Protocol):
    """Reads, adds and deletes annotations."""

    def get_or_create_labels(
        self, dataset_id: UUID, label_names: Sequence[str]
    ) -> list[AnnotationLabelView]:
        """Get annotation labels by name. Create the labels that do not exist."""

    def get_by_sample_ids(self, sample_ids: Sequence[UUID]) -> list[AnnotationView]:
        """Get the annotations of samples."""

    def get_by_sample_ids_and_collection(
        self, sample_ids: Sequence[UUID], annotation_collection_id: UUID
    ) -> list[AnnotationView]:
        """Get the annotations of samples that are in one annotation collection."""

    def get_covered_sequence_ids(self, annotation_collection_id: UUID) -> list[UUID]:
        """Get the IDs of the sequences that have groups covered by the annotation collection.

        The order is not defined.
        """

    def create(
        self,
        parent_collection_id: UUID,
        annotations: Sequence[AnnotationCreate],
        collection_name: str | None,
        covered_sample_ids: Sequence[UUID],
    ) -> list[UUID]:
        """Add annotations to samples.

        Args:
            parent_collection_id: The ID of the collection of the annotated samples.
            annotations: The annotations to add.
            collection_name: The name of the annotation collection. None uses the default.
            covered_sample_ids: Parent samples that the annotation collection covers, also
                samples without annotations.

        Returns:
            The IDs of the new annotations, in the order of `annotations`.
        """

    def update_bounding_box(
        self, annotation_id: UUID, bounding_box: BoundingBoxCoordinates
    ) -> None:
        """Replace the bounding box of an object detection or segmentation mask annotation."""

    def update_segmentation_mask(
        self, annotation_id: UUID, segmentation_mask: Sequence[int]
    ) -> None:
        """Replace the segmentation mask of a segmentation mask annotation."""

    def update_polygons(self, annotation_id: UUID, polygons: Polygons) -> None:
        """Replace the polygons of a polygon annotation and recompute its bounding box."""

    def delete(self, annotation_ids: Sequence[UUID]) -> None:
        """Delete annotations by ID."""

    def delete_empty_object_tracks(self, object_track_ids: Sequence[UUID]) -> int:
        """Delete the object tracks that have no annotations and no child tracks.

        A parent track that becomes empty is also deleted. IDs that do not exist are ignored.

        Returns:
            The number of deleted object tracks.
        """

    # TODO(Iunir, 11/2026): Merge with create_object_tracks. Two clients can get the same numbers.
    def get_free_object_track_numbers(self, dataset_id: UUID, count: int) -> list[int]:
        """Get the `count` lowest positive object track numbers that the dataset does not use."""

    def create_object_tracks(self, tracks: Sequence[ObjectTrackCreate]) -> list[UUID]:
        """Add object tracks.

        Returns:
            The IDs of the new object tracks, in the order of `tracks`.
        """
