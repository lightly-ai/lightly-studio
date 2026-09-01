"""PostHog project an installation reports to.

Internal runs report to the dev project and real users to the production one, so test traffic never
reaches the production project's event volume or person counts. The cohort labels internal usage
inside a project; keeping the projects apart does not depend on a query applying that label.
"""

from __future__ import annotations

from lightly_studio.analytics.cohort import UserCohort
from lightly_studio.dataset.env import LIGHTLY_STUDIO_POSTHOG_KEY

# Write-only keys that ship inside every client anyway, so hardcoding them removes the build time
# variable a release could forget without giving anything away.
DEV_PROJECT_KEY = "phc_A9K0pMRovzmhFhngbKAZIr2qZdA14eHvsZY6kjNdYWr"
PROD_PROJECT_KEY = "phc_LB62TVP2O3S2goH4KASascsXRT14H7zfxHVfo7d2cLV"


def get_project_key(user_cohort: UserCohort) -> str:
    """Get the PostHog project API key an installation in this cohort reports against.

    Args:
        user_cohort: Cohort of this installation.

    Returns:
        `LIGHTLY_STUDIO_POSTHOG_KEY` when set, empty if it switches tracking off. Otherwise the
        production key for real users and the dev key for everyone else.
    """
    if LIGHTLY_STUDIO_POSTHOG_KEY is not None:
        return LIGHTLY_STUDIO_POSTHOG_KEY
    return PROD_PROJECT_KEY if user_cohort is UserCohort.USER else DEV_PROJECT_KEY
