"""Update the cuboid_3d geometry of an annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver


def update_annotation_cuboid_3d(
    session: Session, annotation_id: UUID, cuboid_3d: Cuboid3DCreate
) -> AnnotationBaseTable:
    """Update the cuboid_3d geometry of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        cuboid_3d: New cuboid geometry to assign to the annotation.

    Returns:
        The updated annotation with the new cuboid geometry assigned.

    """
    result = annotation_resolver.update_cuboid_3d(
        session=session,
        annotation_id=annotation_id,
        cuboid_3d=cuboid_3d,
    )
    evaluation_run_resolver.mark_stale_by_collection_id(
        session=session,
        collection_id=result.annotation_collection_id,
    )
    return result
