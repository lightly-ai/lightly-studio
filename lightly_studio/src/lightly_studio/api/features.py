"""Global list of the active features."""

from __future__ import annotations

from importlib import util

from lightly_studio.dataset.env import (
    LIGHTLY_STUDIO_ANALYTICS_ENABLED,
    LIGHTLY_STUDIO_TRAINING_PYTHON,
)

# The GUI reads this back to decide whether to start PostHog, so that
# LIGHTLY_STUDIO_ANALYTICS_ENABLED switches off tracking on both sides.
ANALYTICS_FEATURE = "analytics"
ONBOARDING_FEATURE = "onboarding"
# On when LightlyTrain is installed or a separate training Python is set. The GUI then shows
# "Train model".
TRAINING_FEATURE = "training"


def _get_active_features() -> list[str]:
    """Build the list of features the running app has switched on."""
    features = []
    if LIGHTLY_STUDIO_ANALYTICS_ENABLED:
        features.append(ANALYTICS_FEATURE)
    features.append(ONBOARDING_FEATURE)
    if LIGHTLY_STUDIO_TRAINING_PYTHON or util.find_spec("lightly_train") is not None:
        features.append(TRAINING_FEATURE)
    return features


lightly_studio_active_features: list[str] = _get_active_features()
