"""Job manager for auto-labeling background tasks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.auto_labeling.base_provider import BaseAutoLabelingProvider
from lightly_studio.models.auto_labeling_job import AutoLabelingJobStatus
from lightly_studio.resolvers import auto_labeling_job_resolver, tag_resolver


class AutoLabelingJobManager:
    """Manages background job execution for auto-labeling."""

    def __init__(self):
        # Limit concurrent API-calling jobs to avoid overwhelming external services
        self._executor = ThreadPoolExecutor(max_workers=2)

    def submit_job(
        self,
        job_id: UUID,
        provider: BaseAutoLabelingProvider,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Submit job to background executor.

        Args:
            job_id: ID of the job to execute.
            provider: Provider instance to use for auto-labeling.
            collection_id: Collection to operate on.
            parameters: Parameters for the provider.
        """
        self._executor.submit(
            self._execute_job,
            job_id=job_id,
            provider=provider,
            collection_id=collection_id,
            parameters=parameters,
        )

    def execute_job_sync(
        self,
        session: Session,
        job_id: UUID,
        provider: BaseAutoLabelingProvider,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Execute job synchronously (blocks until complete).

        For prototype use when async execution is not supported.

        Args:
            session: Database session to use.
            job_id: ID of the job to execute.
            provider: Provider instance to use for auto-labeling.
            collection_id: Collection to operate on.
            parameters: Parameters for the provider.
        """
        self._execute_job_with_session(
            session=session,
            job_id=job_id,
            provider=provider,
            collection_id=collection_id,
            parameters=parameters,
        )

    def _execute_job(
        self,
        job_id: UUID,
        provider: BaseAutoLabelingProvider,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Execute job in background thread.

        Args:
            job_id: ID of the job to execute.
            provider: Provider instance to use.
            collection_id: Collection to operate on.
            parameters: Parameters for the provider.
        """
        # Use separate DB session for background thread
        # Note: This requires proper session management - for now using sync execution
        from sqlmodel import Session, create_engine
        from lightly_studio.db_manager import engine

        with Session(engine) as session:
            self._execute_job_with_session(
                session=session,
                job_id=job_id,
                provider=provider,
                collection_id=collection_id,
                parameters=parameters,
            )

    def _execute_job_with_session(
        self,
        session: Session,
        job_id: UUID,
        provider: BaseAutoLabelingProvider,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Execute job with provided session.

        Args:
            session: Database session to use.
            job_id: ID of the job to execute.
            provider: Provider instance to use.
            collection_id: Collection to operate on.
            parameters: Parameters for the provider.
        """
        # Update status to running
        auto_labeling_job_resolver.update_status(
            session,
            job_id,
            AutoLabelingJobStatus.running,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Execute provider
            print(f"[DEBUG] Job manager: About to execute provider {provider.provider_id}")
            print(f"[DEBUG] Job manager: Parameters = {parameters}")

            results = provider.execute(
                session=session,
                collection_id=collection_id,
                parameters=parameters,
            )

            print(f"[DEBUG] Job manager: Provider executed successfully, got {len(results)} results")

            # Count successes/failures
            processed = sum(1 for r in results if r.success)
            errors = sum(1 for r in results if not r.success)

            print(f"[DEBUG] Job manager: Processed {processed} samples, {errors} errors")

            # Print error details
            if errors > 0:
                print("[DEBUG] Job manager: Error details:")
                for r in results:
                    if not r.success:
                        print(f"  - Sample {r.sample_id}: {r.error_message}")

            # Create result tag and apply to samples
            result_tag_name = parameters.get(
                "result_tag_name", f"{provider.provider_id}-processed"
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
            auto_labeling_job_resolver.update_status(
                session,
                job_id,
                AutoLabelingJobStatus.completed,
                processed_count=processed,
                error_count=errors,
                result_tag_id=result_tag.tag_id,
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            # Update job as failed
            print(f"[DEBUG] Job manager: Exception caught: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

            auto_labeling_job_resolver.update_status(
                session,
                job_id,
                AutoLabelingJobStatus.failed,
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )


# Global job manager instance
job_manager = AutoLabelingJobManager()
