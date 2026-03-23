"""Service for reordering annotation layers."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    annotation_layer_resolver,
    annotation_resolver,
    sample_resolver,
)


def reorder_annotation_layers(
    session: Session,
    collection_id: UUID,
    parent_sample_id: UUID,
    ordered_annotation_ids: list[UUID],
) -> None:
    """Persist annotation layer order for one sample.

    Args:
        session: Database session for executing the operation.
        collection_id: Collection identifier from the API path.
        parent_sample_id: Parent sample whose annotation stack is reordered.
        ordered_annotation_ids: Annotation IDs in top-to-bottom order.

    Raises:
        ValueError: If validation fails.
    """
    sample = sample_resolver.get_by_id(session=session, sample_id=parent_sample_id)
    if sample is None:
        raise ValueError(f"Sample with ID {parent_sample_id} not found.")
    if sample.collection_id != collection_id:
        raise ValueError(
            f"Sample {parent_sample_id} does not belong to collection {collection_id}."
        )

    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=session,
        parent_sample_ids=[parent_sample_id],
    )
    existing_annotation_ids = {annotation.sample_id for annotation in annotations}
    if set(ordered_annotation_ids) != existing_annotation_ids:
        raise ValueError("ordered_annotation_ids must match the sample annotations exactly.")

    annotation_layer_resolver.reorder_layers(
        session=session,
        sample_id=parent_sample_id,
        ordered_annotation_ids=ordered_annotation_ids,
    )
