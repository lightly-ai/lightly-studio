"""Global list of the active features."""

from __future__ import annotations

from lightly_studio.dataset.env import LIGHTLY_STUDIO_FEATURE_QUERY_FILTER

QUERY_FILTER_FEATURE = "query_filter"


def _build_active_features() -> list[str]:
    active: list[str] = []
    if LIGHTLY_STUDIO_FEATURE_QUERY_FILTER:
        active.append(QUERY_FILTER_FEATURE)
    return active


lightly_studio_active_features: list[str] = _build_active_features()
