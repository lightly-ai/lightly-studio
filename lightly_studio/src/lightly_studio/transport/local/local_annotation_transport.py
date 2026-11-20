"""Annotation transport that calls the services in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.database import db_manager
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationView
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
    AnnotationLabelView,
)
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_label_resolver,
    annotation_resolver,
    object_track_resolver,
)
from lightly_studio.services import annotations_service


class LocalAnnotationTransport:
    """Implements `AnnotationTransport` with the persistent database session."""

    def get_or_create_labels(
        self, dataset_id: UUID, label_names: Sequence[str]
    ) -> list[AnnotationLabelView]:
        """Get annotation classes by name. Create the classes that do not exist.

        Returns one class for each distinct name, in the order of `label_names`.
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

    def get_by_sample_ids_and_collection(
        self, sample_ids: Sequence[UUID], annotation_collection_id: UUID
    ) -> list[AnnotationView]:
        """Get the annotations of samples that are in one annotation collection."""
        annotations = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
            session=db_manager.persistent_session(),
            parent_sample_ids=sample_ids,
            annotation_collection_id=annotation_collection_id,
            load_view_relationships=True,
        )
        return [
            AnnotationView.from_annotation_table(annotation=annotation)
            for annotation in annotations
        ]

    def get_covered_sequence_ids(self, annotation_collection_id: UUID) -> list[UUID]:
        """Get the sequences with groups that the annotation collection covers."""
        return list(
            annotation_collection_coverage_resolver.sequence_sample_ids(
                session=db_manager.persistent_session(),
                annotation_collection_id=annotation_collection_id,
            )
        )

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
        """Delete annotations by ID. Delete nothing if an annotation does not exist.

        Raises:
            ValueError: If an annotation does not exist.
        """
        session = db_manager.persistent_session()
        found = annotation_resolver.get_by_ids(session=session, annotation_ids=annotation_ids)
        missing_ids = set(annotation_ids) - {annotation.sample_id for annotation in found}
        if missing_ids:
            raise ValueError(f"Annotations not found: {sorted(str(id_) for id_ in missing_ids)}")
        annotation_resolver.delete_annotations_by_ids(
            session=session, annotation_ids=annotation_ids
        )

    def delete_existing(self, annotation_ids: Sequence[UUID]) -> int:
        """Delete annotations by ID. IDs that do not exist are ignored."""
        return annotation_resolver.delete_annotations_by_ids(
            session=db_manager.persistent_session(), annotation_ids=annotation_ids
        )

    def delete_empty_object_tracks(self, object_track_ids: Sequence[UUID]) -> int:
        """Delete the object tracks that have no annotations and no child tracks."""
        return object_track_resolver.delete_empty_by_ids(
            session=db_manager.persistent_session(), object_track_ids=object_track_ids
        )

    def get_free_object_track_numbers(self, dataset_id: UUID, count: int) -> list[int]:
        """Get the `count` lowest positive object track numbers that the dataset does not use."""
        return object_track_resolver.get_free_numbers(
            session=db_manager.persistent_session(), dataset_id=dataset_id, count=count
        )

    def create_object_tracks(self, tracks: Sequence[ObjectTrackCreate]) -> list[UUID]:
        """Add object tracks."""
        return object_track_resolver.create_many(
            session=db_manager.persistent_session(), tracks=list(tracks)
        )


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
