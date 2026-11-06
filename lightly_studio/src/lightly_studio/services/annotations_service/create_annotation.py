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
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
    object_track_resolver,
)


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
    and the annotation is linked to it.

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
        new_annotation_ids = annotation_resolver.create_many(
            session=session,
            parent_collection_id=annotation.collection_id,
            annotations=[AnnotationCreate(**annotation_data)],
            collection_name=annotation.annotation_collection_name,
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

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=session,
        collection_id=created_annotation.annotation_collection_id,
    )

    return created_annotation


def _resolve_object_track_id(session: Session, annotation: AnnotationCreateParams) -> UUID | None:
    if annotation.create_new_track and annotation.object_track_id is not None:
        raise ValueError("Cannot set both create_new_track and object_track_id.")
    if not annotation.create_new_track:
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
    return _create_object_track(session=session, dataset_id=collection.dataset_id)


def _create_object_track(session: Session, dataset_id: UUID) -> UUID:
    track_number = object_track_resolver.next_track_number(session=session, dataset_id=dataset_id)
    track_ids = object_track_resolver.create_many(
        session=session,
        tracks=[ObjectTrackCreate(object_track_number=track_number, dataset_id=dataset_id)],
        commit=False,
    )
    return track_ids[0]
