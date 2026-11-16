"""Transport protocol for annotations and annotation labels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationView
from lightly_studio.models.annotation_label import AnnotationLabelView


class AnnotationTransport(Protocol):
    """Reads, adds and deletes annotations."""

    def get_or_create_labels(
        self, dataset_id: UUID, label_names: Sequence[str]
    ) -> list[AnnotationLabelView]:
        """Get annotation labels by name. Create the labels that do not exist."""

    def get_by_sample_ids(self, sample_ids: Sequence[UUID]) -> list[AnnotationView]:
        """Get the annotations of samples."""

    def create(
        self,
        parent_collection_id: UUID,
        annotations: Sequence[AnnotationCreate],
        collection_name: str | None,
    ) -> list[UUID]:
        """Add annotations to samples.

        Args:
            parent_collection_id: The ID of the collection of the annotated samples.
            annotations: The annotations to add.
            collection_name: The name of the annotation collection. None uses the default.

        Returns:
            The IDs of the new annotations, in the order of `annotations`.
        """

    def delete(self, annotation_ids: Sequence[UUID]) -> None:
        """Delete annotations by ID."""
