"""Annotation transport that calls the services in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.database import db_manager
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationView
from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
    AnnotationLabelView,
)
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver
from lightly_studio.services import annotations_service


class LocalAnnotationTransport:
    """Implements `AnnotationTransport` with the persistent database session."""

    def get_or_create_labels(
        self, dataset_id: UUID, label_names: Sequence[str]
    ) -> list[AnnotationLabelView]:
        """Get annotation labels by name. Create the labels that do not exist.

        Returns one label for each distinct name, in the order of `label_names`.
        """
        session = db_manager.persistent_session()
        return [
            AnnotationLabelView.model_validate(
                _get_or_create_label(session=session, dataset_id=dataset_id, label_name=name)
            )
            for name in dict.fromkeys(label_names)
        ]

    def get_by_sample_ids(self, sample_ids: Sequence[UUID]) -> list[AnnotationView]:
        """Get the annotations of samples."""
        annotations = annotation_resolver.get_all_by_parent_sample_ids(
            session=db_manager.persistent_session(), parent_sample_ids=sample_ids
        )
        return [
            AnnotationView.from_annotation_table(annotation=annotation)
            for annotation in annotations
        ]

    def create(
        self,
        parent_collection_id: UUID,
        annotations: Sequence[AnnotationCreate],
        collection_name: str | None,
        covered_sample_ids: Sequence[UUID],
    ) -> list[UUID]:
        """Add annotations to samples. Mark the evaluation runs of their source stale."""
        return annotations_service.create_annotations(
            session=db_manager.persistent_session(),
            parent_collection_id=parent_collection_id,
            annotations=annotations,
            collection_name=collection_name,
            covered_sample_ids=covered_sample_ids,
        )

    def delete(self, annotation_ids: Sequence[UUID]) -> None:
        """Delete annotations by ID.

        Raises:
            ValueError: If an annotation does not exist.
        """
        session = db_manager.persistent_session()
        for annotation_id in annotation_ids:
            annotations_service.delete_annotation(session=session, annotation_id=annotation_id)


def _get_or_create_label(
    session: Session, dataset_id: UUID, label_name: str
) -> AnnotationLabelTable:
    label = annotation_label_resolver.get_by_label_name(
        session=session, dataset_id=dataset_id, label_name=label_name
    )
    if label is not None:
        return label
    return annotation_label_resolver.create(
        session=session,
        label=AnnotationLabelCreate(dataset_id=dataset_id, annotation_label_name=label_name),
    )
