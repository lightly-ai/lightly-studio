"""Views of the assisted labeling providers."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.assisted_labeling import registry
from lightly_studio.assisted_labeling.provider import AssistedLabelingProvider
from lightly_studio.models.assisted_labeling import AssistedLabelingProviderView
from lightly_studio.services.assisted_labeling_service import get_active_provider


def get_active_provider_view(session: Session) -> AssistedLabelingProviderView:
    """Returns the view of the provider that the settings select.

    Raises:
        ValueError: If the settings select an unknown provider.
    """
    provider = get_active_provider.get_active_provider(session=session)
    return _to_view(provider=provider)


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
