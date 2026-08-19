"""Global list of the active features."""

from __future__ import annotations

from lightly_studio.dataset.env import LIGHTLY_STUDIO_ANALYTICS_ENABLED

# The GUI reads this back to decide whether to start PostHog, so that
# LIGHTLY_STUDIO_ANALYTICS_ENABLED switches off tracking on both sides.
ANALYTICS_FEATURE = "analytics"


def _get_active_features() -> list[str]:
    """Build the list of features the running app has switched on."""
    features = []
    if LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        features.append(ANALYTICS_FEATURE)
    return features


lightly_studio_active_features: list[str] = _get_active_features()
