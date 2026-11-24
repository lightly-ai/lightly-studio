"""Query the images that an evaluation run evaluated."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.sample import SampleTagLinkTable


def get_sample_ids_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
    tag_id: UUID | None = None,
) -> list[UUID]:
    """Return the distinct IDs of the images that a run evaluated, sorted.

    Args:
        session: Database session.
        evaluation_run_id: The evaluation run.
        tag_id: If set, return only the evaluated images with this tag.

    Returns:
        The sorted sample IDs of the evaluated images.
    """
    stmt = (
        select(EvaluationSampleMetricTable.sample_id)
        .where(col(EvaluationSampleMetricTable.evaluation_run_id) == evaluation_run_id)
        .distinct()
    )
    if tag_id is not None:
        tagged_sample_ids = select(SampleTagLinkTable.sample_id).where(
            col(SampleTagLinkTable.tag_id) == tag_id
        )
        stmt = stmt.where(col(EvaluationSampleMetricTable.sample_id).in_(tagged_sample_ids))
    return sorted(session.exec(stmt).all(), key=str)
