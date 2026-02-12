"""Job manager for plugin background tasks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.plugins.base_operator import BatchSampleOperator
from lightly_studio.models.plugin_job import PluginJobStatus
from lightly_studio.resolvers import plugin_job_resolver, tag_resolver


class PluginJobManager:
    """Manages background job execution for batch sample operators."""

    def __init__(self):
        # Limit concurrent API-calling jobs to avoid overwhelming external services
        self._executor = ThreadPoolExecutor(max_workers=2)

    def submit_job(
        self,
        job_id: UUID,
        operator: BatchSampleOperator,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Submit job to background executor.

        Args:
            job_id: ID of the job to execute.
            operator: BatchSampleOperator instance to use.
            collection_id: Collection to operate on.
            parameters: Parameters for the operator.
        """
        self._executor.submit(
            self._execute_job,
            job_id=job_id,
            operator=operator,
            collection_id=collection_id,
            parameters=parameters,
        )

    def execute_job_sync(
        self,
        session: Session,
        job_id: UUID,
        operator: BatchSampleOperator,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Execute job synchronously (blocks until complete).

        For prototype use when async execution is not supported.

        Args:
            session: Database session to use.
            job_id: ID of the job to execute.
            operator: BatchSampleOperator instance to use.
            collection_id: Collection to operate on.
            parameters: Parameters for the operator.
        """
        self._execute_job_with_session(
            session=session,
            job_id=job_id,
            operator=operator,
            collection_id=collection_id,
            parameters=parameters,
        )

    def _execute_job(
        self,
        job_id: UUID,
        operator: BatchSampleOperator,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Execute job in background thread."""
        from sqlmodel import Session, create_engine
        from lightly_studio.db_manager import engine

        with Session(engine) as session:
            self._execute_job_with_session(
                session=session,
                job_id=job_id,
                operator=operator,
                collection_id=collection_id,
                parameters=parameters,
            )

    def _execute_job_with_session(
        self,
        session: Session,
        job_id: UUID,
        operator: BatchSampleOperator,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Execute job with provided session."""
        # Update status to running
        plugin_job_resolver.update_status(
            session,
            job_id,
            PluginJobStatus.running,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Execute operator batch
            results = operator.execute_batch(
                session=session,
                collection_id=collection_id,
                parameters=parameters,
            )

            # Count successes/failures
            processed = sum(1 for r in results if r.success)
            errors = sum(1 for r in results if not r.success)

            # Create result tag and apply to samples
            result_tag_name = parameters.get(
                "result_tag_name", f"{operator.name}-processed"
            )
            result_tag = tag_resolver.get_or_create_sample_tag_by_name(
                session=session,
                collection_id=collection_id,
                tag_name=result_tag_name,
            )

            # Apply tag to all successfully processed samples
            successful_sample_ids = [r.sample_id for r in results if r.success]
            if successful_sample_ids:
                tag_resolver.add_sample_ids_to_tag_id(
                    session=session,
                    tag_id=result_tag.tag_id,
                    sample_ids=successful_sample_ids,
                )

            # Update job as completed
            plugin_job_resolver.update_status(
                session,
                job_id,
                PluginJobStatus.completed,
                processed_count=processed,
                error_count=errors,
                result_tag_id=result_tag.tag_id,
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            plugin_job_resolver.update_status(
                session,
                job_id,
                PluginJobStatus.failed,
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )


# Global job manager instance
job_manager = PluginJobManager()
