"""Views of the assisted labeling providers."""

from __future__ import annotations

from lightly_studio.assisted_labeling import registry
from lightly_studio.assisted_labeling.provider import AssistedLabelingProvider
from lightly_studio.models.assisted_labeling import AssistedLabelingProviderView


def list_provider_views() -> list[AssistedLabelingProviderView]:
    """Returns the views of all providers."""
    return [_to_view(provider=provider) for provider in registry.list_providers()]


def _to_view(provider: AssistedLabelingProvider) -> AssistedLabelingProviderView:
    return AssistedLabelingProviderView(
        provider_id=provider.provider_id,
        display_name=provider.display_name,
        sends_data_to_third_party=provider.sends_data_to_third_party,
        capabilities=provider.capabilities(),
        unavailable_reason=provider.is_available(),
    )
