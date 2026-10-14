"""Module for handling the update of cuboid_3d geometry in the database."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper


def update_cuboid_3d(
    session: Session,
    annotation_id: UUID,
    cuboid_3d: Cuboid3DCreate,
) -> AnnotationBaseTable:
    """Update the cuboid_3d geometry of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        cuboid_3d: New cuboid geometry to assign to the annotation.

    Returns:
        The updated annotation with the new cuboid geometry.

    Raises:
        ValueError: If the annotation is not found or is not a cuboid_3d annotation.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")
    if annotation.annotation_type != AnnotationType.CUBOID_3D:
        raise ValueError("Annotation type does not support cuboid_3d updates.")
    annotation_helper.update_annotation_object(
        session=session,
        annotation=annotation,
        fields_to_update=None,
        cuboid_3d=cuboid_3d,
    )
    # Re-fetch to get a session-bound instance with updated relationship data.
    refreshed = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    assert refreshed is not None
    return refreshed
