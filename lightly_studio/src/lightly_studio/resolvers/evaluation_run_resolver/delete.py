"""Delete a saved evaluation and its metrics."""

from sqlmodel import Session

from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)


def delete(session: Session, run: EvaluationRunTable) -> None:
    """Delete only the run and its metrics, preserving source annotations."""
    evaluation_annotation_metric_resolver.delete_by_evaluation_run_id(
        session=session, evaluation_run_id=run.id
    )
    evaluation_sample_metric_resolver.delete_by_evaluation_run_id(
        session=session, evaluation_run_id=run.id
    )
    # DuckDB cannot delete a referenced run until its metric deletions are committed.
    session.commit()
    session.delete(run)
    session.commit()
