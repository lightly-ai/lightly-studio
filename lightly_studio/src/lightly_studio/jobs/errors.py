"""Errors raised by background jobs."""

from __future__ import annotations

from uuid import UUID


class JobError(Exception):
    """Base class of all job errors."""


class RetryableJobError(JobError):
    """A job attempt failed for a temporary reason. The engine retries the job."""


class NonRetryableJobError(JobError):
    """A job failed for a reason that a retry cannot fix. The job fails at once."""


class SignatureError(NonRetryableJobError):
    """The signature of a job payload is not valid."""


class RevisionMismatchError(NonRetryableJobError):
    """The schema revision of the tenant database is not the revision of the worker."""


class TenantMismatchError(NonRetryableJobError):
    """A job payload names a tenant that the worker does not serve."""


class JobConflictError(JobError):
    """A job cannot start because a job is already active for the same resource.

    Attributes:
        active_job_id: The ID of the active job.
    """

    def __init__(self, active_job_id: UUID) -> None:
        """Creates the error for the active job with ID `active_job_id`."""
        super().__init__("A job is already active for this resource.")
        self.active_job_id = active_job_id


class UnknownJobTypeError(JobError, ValueError):
    """No job type is registered with the requested name."""


class JobsNotConfiguredError(JobError):
    """Jobs are not configured. The signing secret or the engine token is not set."""

    def __init__(self) -> None:
        """Creates the error with a message for the user."""
        super().__init__("Jobs are not configured.")
