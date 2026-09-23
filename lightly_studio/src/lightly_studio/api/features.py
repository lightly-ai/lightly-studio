"""Global list of the active features."""

from __future__ import annotations

from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_ANALYTICS_ENABLED,
    LIGHTLY_STUDIO_POINT_CLOUD_ENABLED,
)

# The GUI reads this back to decide whether to start PostHog, so that
# LIGHTLY_STUDIO_ANALYTICS_ENABLED switches off tracking on both sides.
ANALYTICS_FEATURE = "analytics"
# The GUI reads this back to decide whether MCAP samples can open the point-cloud labeling
# workspace (LIG-10659). Leaving it off never affects the existing sample detail view.
POINT_CLOUD_RENDERING_FEATURE = "point_cloud_rendering"


def _get_active_features() -> list[str]:
    """Build the list of features the running app has switched on."""
    features = []
    if LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        features.append(ANALYTICS_FEATURE)
    if LIGHTLY_STUDIO_POINT_CLOUD_ENABLED:
        features.append(POINT_CLOUD_RENDERING_FEATURE)
    return features


lightly_studio_active_features: list[str] = _get_active_features()
