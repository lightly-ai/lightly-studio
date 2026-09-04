"""Tracker sending usage events to PostHog."""

from __future__ import annotations

import logging
import platform
from collections.abc import Mapping
from importlib import metadata

from posthog import Posthog

from lightly_studio.analytics import cohort, install_id
from lightly_studio.analytics.tracker import Tracker

# One retry rather than the default three. Delivery happens on a background thread, but the flush
# at process exit blocks on it, and nobody should wait on telemetry to close the CLI.
MAX_RETRIES = 1
REQUEST_TIMEOUT_SECONDS = 3

# PostHog reports delivery failures at ERROR, and the retries around them at INFO, straight to the
# user's terminal. An unreachable analytics endpoint is not the user's problem. Both names are
# needed: PostHog's consumer wraps its send in `backoff.on_exception` without passing a logger, so
# the retry lines go to `backoff`'s own logger rather than PostHog's.
_NOISY_LOGGERS = ("posthog", "backoff")

# Reported when the distribution metadata is missing, so when running straight from a checkout.
UNKNOWN_VERSION = "unknown"


class PostHogTracker(Tracker):
    """Sends usage events to PostHog.

    Events are initially keyed on the anonymous installation ID. After ``identify`` is called, the
    tracker switches to the user's email as the distinct ID and all subsequent events are keyed on
    that instead.

    Events are queued and delivered by a background thread, so ``track`` does not block. Call
    ``shutdown`` before the process ends, otherwise queued events are lost.
    """

    def __init__(self, project_api_key: str, host: str) -> None:
        """Build the tracker.

        Args:
            project_api_key: PostHog project API key to report against.
            host: PostHog instance to report to.
        """
        self._client = Posthog(
            project_api_key=project_api_key,
            host=host,
            max_retries=MAX_RETRIES,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        _silence_delivery_logging()
        self._distinct_id = str(install_id.get_install_id())
        self._common_properties = _common_properties()

    def identify(self, email: str) -> None:
        """Link the anonymous install ID to a known user and switch identity.

        Calls ``alias`` so PostHog merges the pre-identification anonymous
        events with the identified user, then switches ``distinct_id`` for all
        subsequent ``track`` calls.

        Args:
            email: User email from the enterprise auth service.
        """
        self._client.alias(previous_id=self._distinct_id, distinct_id=email)
        self._distinct_id = email

    def track(self, event: str, properties: Mapping[str, object]) -> None:
        """Queue an event for delivery.

        Args:
            event: Event name.
            properties: Metadata to attach, merged over the properties sent with every event.
        """
        self._client.capture(
            event=event,
            distinct_id=self._distinct_id,
            properties={**self._common_properties, **properties},
        )

    def shutdown(self) -> None:
        """Flush queued events and stop the background thread."""
        self._client.shutdown()


def _silence_delivery_logging() -> None:
    """Keep delivery failures out of the handlers that write to the user's terminal.

    Stops propagation rather than raising the level, so a caller that attached a handler to these
    loggers itself still receives the records.
    """
    for name in _NOISY_LOGGERS:
        logger = logging.getLogger(name)
        # Without a handler of its own, a logger that does not propagate falls back to
        # `logging.lastResort`, which writes to stderr. The null handler is what stops that.
        logger.addHandler(logging.NullHandler())
        logger.propagate = False


def _common_properties() -> dict[str, object]:
    """Build the properties attached to every event."""
    user_cohort = cohort.get_cohort().value
    return {
        "lightly_studio_version": _version(),
        "python_version": platform.python_version(),
        "os": platform.system(),
        "user_cohort": user_cohort,
        # Also stored on the person, so a PostHog cohort and the project-wide internal user filter
        # can select on it without reading event properties.
        "$set": {"user_cohort": user_cohort},
    }


def _version() -> str:
    """Get the version of the installed package, `UNKNOWN_VERSION` when it is not installed.

    Raising instead would cost the event, and an uninstalled checkout is the `SOURCE_BUILD` cohort.
    """
    try:
        return metadata.version("lightly-studio")
    except metadata.PackageNotFoundError:
        return UNKNOWN_VERSION
