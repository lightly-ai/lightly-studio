"""Shared error type for the prepare-release tooling."""


class PrepareReleaseError(Exception):
    """A release-preparation precondition failed.

    Raised for anything that should fail the workflow loudly rather than
    open a malformed or unreviewable release PR.
    """
