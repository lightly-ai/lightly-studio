"""Delete the class metrics of an annotation label."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricTable


def delete_by_annotation_label_id(session: Session, annotation_label_id: UUID) -> None:
    """Delete all class metrics of the given annotation label.

    The DELETE runs in the current transaction but is not committed.
    The caller commits or rolls back.
    """
    session.exec(
        delete(EvaluationClassMetricTable).where(
            col(EvaluationClassMetricTable.annotation_label_id) == annotation_label_id
        )
    )
