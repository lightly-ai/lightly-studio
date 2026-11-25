"""Get the names of the evaluation runs that use an annotation collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, or_, select

from lightly_studio.models.evaluation_run import EvaluationRunTable


def get_names_by_collection_id(session: Session, collection_id: UUID) -> list[str]:
    """Return the names of the evaluation runs that use the annotation collection.

    Args:
        session: Database session.
        collection_id: ID of the ground truth or prediction annotation collection.

    Returns:
        The run names in alphabetical order.
    """
    return list(
        session.exec(
            select(EvaluationRunTable.name)
            .where(
                or_(
                    col(EvaluationRunTable.gt_annotation_collection_id) == collection_id,
                    col(EvaluationRunTable.pred_annotation_collection_id) == collection_id,
                )
            )
            .order_by(col(EvaluationRunTable.name))
        ).all()
    )
