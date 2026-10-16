"""API models for assisted labeling."""

from __future__ import annotations

from pydantic import BaseModel

from lightly_studio.assisted_labeling.provider import ProviderCapabilities


class AssistedLabelingProviderView(BaseModel):
    """An assisted labeling provider and its state.

    Attributes:
        provider_id: Stable ID of the provider.
        display_name: Human-readable name of the provider.
        sends_data_to_third_party: True if the provider sends image data to a third party.
        capabilities: Prompt types and limits that the provider supports.
        unavailable_reason: None if the provider is usable, else the reason why not.
    """

    provider_id: str
    display_name: str
    sends_data_to_third_party: bool
    capabilities: ProviderCapabilities
    unavailable_reason: str | None
