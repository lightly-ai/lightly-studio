"""Resolvers for annotation layer ordering."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_layer import AnnotationLayerTable


def create_layers_for_annotations(
    session: Session,
    annotation_ids_with_parent_sample_ids: Sequence[tuple[UUID, UUID]],
) -> None:
    """Create layer rows for new annotations at the top of each parent sample stack."""
    if not annotation_ids_with_parent_sample_ids:
        return

    sample_ids = {sample_id for _, sample_id in annotation_ids_with_parent_sample_ids}
    max_positions = _get_max_positions_by_sample_id(session=session, sample_ids=sample_ids)

    layers: list[AnnotationLayerTable] = []
    for annotation_id, parent_sample_id in annotation_ids_with_parent_sample_ids:
        position = max_positions.get(parent_sample_id, 0) + 1
        max_positions[parent_sample_id] = position
        layers.append(
            AnnotationLayerTable(
                annotation_id=annotation_id,
                sample_id=parent_sample_id,
                position=position,
            )
        )

    session.bulk_save_objects(layers)
    session.flush()


def ensure_layers_for_annotations(
    session: Session,
    annotation_ids: Sequence[UUID],
) -> None:
    """Ensure all provided annotations have a matching layer row."""
    if not annotation_ids:
        return

    annotation_ids_set = set(annotation_ids)
    existing_layer_annotation_ids = set(
        session.exec(
            select(AnnotationLayerTable.annotation_id).where(
                col(AnnotationLayerTable.annotation_id).in_(annotation_ids_set)
            )
        ).all()
    )
    missing_annotation_ids = annotation_ids_set.difference(existing_layer_annotation_ids)
    if not missing_annotation_ids:
        return

    annotations = session.exec(
        select(AnnotationBaseTable)
        .where(col(AnnotationBaseTable.sample_id).in_(missing_annotation_ids))
        .order_by(
            col(AnnotationBaseTable.created_at).asc(),
            col(AnnotationBaseTable.sample_id).asc(),
        )
    ).all()
    annotation_pairs = [
        (annotation.sample_id, annotation.parent_sample_id) for annotation in annotations
    ]
    create_layers_for_annotations(
        session=session,
        annotation_ids_with_parent_sample_ids=annotation_pairs,
    )


def move_annotation_to_top(
    session: Session,
    annotation_id: UUID,
) -> AnnotationLayerTable:
    """Move one annotation layer to the top of its parent sample stack."""
    ensure_layers_for_annotations(session=session, annotation_ids=[annotation_id])

    layer = session.exec(
        select(AnnotationLayerTable).where(col(AnnotationLayerTable.annotation_id) == annotation_id)
    ).one_or_none()
    if layer is None:
        raise ValueError(f"Layer for annotation {annotation_id} not found.")

    current_top = session.exec(
        select(func.max(col(AnnotationLayerTable.position))).where(
            col(AnnotationLayerTable.sample_id) == layer.sample_id
        )
    ).one()
    top_position = int(current_top or 0)
    layer.position = top_position + 1
    session.add(layer)
    session.commit()
    session.refresh(layer)
    return layer


def reorder_layers(
    session: Session,
    sample_id: UUID,
    ordered_annotation_ids: Sequence[UUID],
) -> list[AnnotationLayerTable]:
    """Persist layer positions for one sample from top to bottom."""
    if not ordered_annotation_ids:
        raise ValueError("ordered_annotation_ids cannot be empty.")

    ordered_ids = list(ordered_annotation_ids)
    if len(set(ordered_ids)) != len(ordered_ids):
        raise ValueError("ordered_annotation_ids must not contain duplicates.")

    ensure_layers_for_annotations(session=session, annotation_ids=ordered_ids)

    sample_layers = session.exec(
        select(AnnotationLayerTable).where(col(AnnotationLayerTable.sample_id) == sample_id)
    ).all()
    layer_by_annotation_id = {layer.annotation_id: layer for layer in sample_layers}

    if set(layer_by_annotation_id.keys()) != set(ordered_ids):
        raise ValueError("ordered_annotation_ids must match the sample annotations exactly.")

    for position, annotation_id in enumerate(reversed(ordered_ids), start=1):
        layer = layer_by_annotation_id[annotation_id]
        layer.position = position
        session.add(layer)

    session.commit()
    return [layer_by_annotation_id[annotation_id] for annotation_id in ordered_ids]


def _get_max_positions_by_sample_id(
    session: Session,
    sample_ids: set[UUID],
) -> dict[UUID, int]:
    if not sample_ids:
        return {}

    rows = session.exec(
        select(
            AnnotationLayerTable.sample_id,
            func.max(col(AnnotationLayerTable.position)),
        )
        .where(col(AnnotationLayerTable.sample_id).in_(sample_ids))
        .group_by(col(AnnotationLayerTable.sample_id))
    ).all()
    return {sample_id: int(max_position or 0) for sample_id, max_position in rows}
