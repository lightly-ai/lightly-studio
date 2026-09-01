"""Anonymous usage tracking.

Call sites use `track` and nothing else. Which backend receives the events is an implementation
detail of this module, so replacing or dropping PostHog does not touch any caller.
"""

from __future__ import annotations

import atexit
import logging
import threading
from collections.abc import Mapping
from enum import Enum

from lightly_studio.analytics import cohort, posthog_project
from lightly_studio.analytics.posthog_tracker import PostHogTracker
from lightly_studio.analytics.tracker import Tracker
from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_ANALYTICS_ENABLED,
    LIGHTLY_STUDIO_POSTHOG_HOST,
)

logger = logging.getLogger(__name__)

APP_LAUNCHED = "app_launched"


class NoOpTracker(Tracker):
    """Tracker that drops everything, used when tracking is off."""

    def track(self, event: str, properties: Mapping[str, object]) -> None:
        """Discard the event."""

    def shutdown(self) -> None:
        """Do nothing."""


class LaunchSource(str, Enum):
    """The entry point that started the app."""

    QUICKSTART = "quickstart"
    GUI = "gui"


def track(event: str, properties: Mapping[str, object]) -> None:
    """Report a usage event.

    Never raises. Tracking is best effort and must not be able to break the caller.

    Args:
        event: Event name, e.g. `APP_LAUNCHED`.
        properties: Metadata to attach to the event.
    """
    try:
        _get_tracker().track(event=event, properties=properties)
    except Exception:
        logger.debug(f"Could not report the '{event}' event.", exc_info=True)


def shutdown() -> None:
    """Deliver pending events and release the tracker. Never raises."""
    global _tracker  # noqa: PLW0603
    # Only the swap is locked. Flushing can block on the network, and a caller reporting an event
    # meanwhile should not wait on it.
    with _tracker_lock:
        tracker = _tracker
        _tracker = None

    if tracker is None:
        return

    try:
        tracker.shutdown()
    except Exception:
        logger.debug("Could not shut down the tracker.", exc_info=True)


_tracker: Tracker | None = None
_tracker_lock = threading.Lock()


def _get_tracker() -> Tracker:
    """Get the process-wide tracker, building it on first use."""
    global _tracker  # noqa: PLW0603
    # Held for the whole check-and-build: two callers racing here would each get a tracker, and
    # the loser's events would sit in an instance nothing ever flushes.
    with _tracker_lock:
        if _tracker is None:
            _tracker = _create_tracker()
        return _tracker


def _create_tracker() -> Tracker:
    """Build the tracker matching the current configuration."""
    if not LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        return NoOpTracker()

    project_api_key = posthog_project.get_project_key(cohort.get_cohort())
    tracker = PostHogTracker(project_api_key=project_api_key, host=LIGHTLY_STUDIO_POSTHOG_HOST)
    # PostHog delivers from a background thread and registers no exit hook of its own, so a
    # short-lived process would drop the event without this.
    atexit.register(shutdown)
    return tracker
