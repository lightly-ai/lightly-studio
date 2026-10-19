"""API models for assisted labeling."""

from __future__ import annotations

from pydantic import BaseModel


class AssistedLabelingStatusView(BaseModel):
    """State of assisted labeling.

    Attributes:
        unavailable_reason: None if assisted labeling is usable, else the reason why not.
    """

    unavailable_reason: str | None
