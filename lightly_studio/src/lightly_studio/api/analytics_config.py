"""Analytics configuration the GUI reads back from the backend.

The GUI reports to the same PostHog project as the Python package, so deciding here keeps one
source of truth for whether tracking runs, under which identity, and in which cohort.
"""

from __future__ import annotations

from pydantic import BaseModel

from lightly_studio.analytics import cohort, install_id
from lightly_studio.analytics.cohort import UserCohort
from lightly_studio.dataset.env import LIGHTLY_STUDIO_ANALYTICS_ENABLED


class AnalyticsConfigView(BaseModel):
    """Analytics configuration of the running app.

    Attributes:
        enabled: Whether usage tracking is switched on.
        distinct_id: Anonymous ID the GUI reports against, shared with the Python package so that
            backend and browser events belong to one person. None while tracking is off.
        user_cohort: Cohort of this installation, keeping internal usage out of the product
            metrics. None while tracking is off.
    """

    enabled: bool
    distinct_id: str | None
    user_cohort: UserCohort | None


def get_analytics_config() -> AnalyticsConfigView:
    """Build the analytics configuration for the running app."""
    if not LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        # Reading the installation ID writes it to disk on first use, which opting out must not
        # trigger.
        return AnalyticsConfigView(enabled=False, distinct_id=None, user_cohort=None)

    return AnalyticsConfigView(
        enabled=True,
        distinct_id=str(install_id.get_install_id()),
        user_cohort=cohort.get_cohort(),
    )
