"""Global list of the active features."""

from __future__ import annotations

from lightly_studio.dataset.env import LIGHTLY_STUDIO_ANALYTICS_ENABLED

# Reports whether usage tracking runs. The GUI decides whether to start PostHog from
# /analytics/config instead, which also carries the identity to report under.
ANALYTICS_FEATURE = "analytics"


def _get_active_features() -> list[str]:
    """Build the list of features the running app has switched on."""
    features = []
    if LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        features.append(ANALYTICS_FEATURE)
    return features


lightly_studio_active_features: list[str] = _get_active_features()
