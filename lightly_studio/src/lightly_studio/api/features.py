"""Global list of the active features."""

from __future__ import annotations

from lightly_studio.dataset.env import LIGHTLY_STUDIO_FEATURE_QUERY_FILTER

lightly_studio_active_features: list[str] = []

if LIGHTLY_STUDIO_FEATURE_QUERY_FILTER:
    lightly_studio_active_features.append("query_filter")
