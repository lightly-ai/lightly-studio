"""Create annotation."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    object_track_resolver,
)
from lightly_studio.services import annotations_service, object_track_service


class AnnotationCreateParams(BaseModel):
    """Input model for create annotation service.

    If annotation_collection_name is None, a default name is set.
    """

    annotation_label_id: UUID
    annotation_type: AnnotationType
    annotation_collection_name: str | None = None
    collection_id: UUID
    parent_sample_id: UUID
    object_track_id: UUID | None = None
    create_new_track: bool = False

    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None

    segmentation_mask: list[int] | None = None

    start_time_s: float | None = None
    end_time_s: float | None = None
    cuboid_3d: Cuboid3DCreate | None = None


def create_annotation(session: Session, annotation: AnnotationCreateParams) -> AnnotationBaseTable:
    """Create a new annotation.

    When ``create_new_track`` is set, a new :class:`ObjectTrackTable` row is
    created atomically with the next available track number for the dataset,
    and the annotation is linked to it. A cuboid added to a track interpolates the track
    around it.

    Args:
        session: Database session for executing the operation.
        annotation: Annotation data to create.

    Returns:
        The retrieved annotation.
    """
    try:
        annotation_data = annotation.model_dump(exclude={"create_new_track"})
        annotation_data["object_track_id"] = _resolve_object_track_id(
            session=session, annotation=annotation
        )
        new_annotation_ids = annotations_service.create_annotations(
            session=session,
            parent_collection_id=annotation.collection_id,
            annotations=[AnnotationCreate(**annotation_data)],
            collection_name=annotation.annotation_collection_name,
            covered_sample_ids=[],
        )
    except Exception:
        session.rollback()
        raise

    if not new_annotation_ids:
        raise ValueError("Failed to create annotation.")

    created_annotation = annotation_resolver.get_by_id(
        session=session,
        annotation_id=new_annotation_ids[0],
    )

    if created_annotation is None:
        raise ValueError(f"Failed to create annotation: {annotation}")

    if annotation.object_track_id is not None:
        object_track_service.interpolate_around_cuboid(
            session=session, annotation_id=created_annotation.sample_id
        )

    return created_annotation


def _resolve_object_track_id(session: Session, annotation: AnnotationCreateParams) -> UUID | None:
    if annotation.create_new_track and annotation.object_track_id is not None:
        raise ValueError("Cannot set both create_new_track and object_track_id.")
    if not annotation.create_new_track:
        if annotation.object_track_id is not None:
            _validate_object_track(
                session=session,
                object_track_id=annotation.object_track_id,
                collection_id=annotation.collection_id,
            )
            _validate_track_has_no_cuboid(
                session=session,
                object_track_id=annotation.object_track_id,
                annotation_type=annotation.annotation_type,
                parent_sample_id=annotation.parent_sample_id,
            )
        return annotation.object_track_id

    collection = collection_resolver.get_by_id(
        session=session, collection_id=annotation.collection_id
    )
    if collection is None:
        raise ValueError(f"Collection {annotation.collection_id} not found.")
    # Source creation commits, so prepare it before inserting the uncommitted track.
    collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=annotation.collection_id,
        sample_type=SampleType.ANNOTATION,
        name=annotation.annotation_collection_name,
    )
    track = object_track_resolver.create_with_next_number(
        session=session, dataset_id=collection.dataset_id, commit=False
    )
    return track.object_track_id


def _validate_object_track(session: Session, object_track_id: UUID, collection_id: UUID) -> None:
    track = object_track_resolver.get_by_id(session=session, object_track_id=object_track_id)
    if track is None:
        raise ValueError(f"Object track {object_track_id} not found.")
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection {collection_id} not found.")
    if track.dataset_id != collection.dataset_id:
        raise ValueError(
            f"Object track {object_track_id} belongs to a different dataset"
            f" than collection {collection_id}."
        )


def _validate_track_has_no_cuboid(
    session: Session,
    object_track_id: UUID,
    annotation_type: AnnotationType,
    parent_sample_id: UUID,
) -> None:
    # An object track has at most one cuboid on each group. An undone delete can
    # recreate a cuboid in a track that has a new cuboid on the same group.
    if annotation_type != AnnotationType.CUBOID_3D:
        return
    if object_track_resolver.has_cuboid_on_parent_sample(
        session=session,
        object_track_id=object_track_id,
        parent_sample_id=parent_sample_id,
    ):
        raise ValueError("A cuboid for this object track already exists on this group.")
