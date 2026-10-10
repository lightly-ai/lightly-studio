"""Lookup of the assisted labeling provider that the settings select."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.assisted_labeling import registry
from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    ProviderUnavailableError,
)
from lightly_studio.resolvers import settings_resolver


def get_active_provider(session: Session) -> AssistedLabelingProvider:
    """Returns the provider that the settings select.

    Raises:
        ValueError: If the settings select an unknown provider.
    """
    settings = settings_resolver.get_settings(session=session)
    return registry.get_provider(provider_id=settings.assisted_labeling_provider)


def get_usable_provider(session: Session) -> AssistedLabelingProvider:
    """Returns the provider that the settings select if it is usable.

    Raises:
        ValueError: If the settings select an unknown provider.
        ProviderUnavailableError: If the provider is not usable.
    """
    provider = get_active_provider(session=session)
    unavailable_reason = provider.is_available()
    if unavailable_reason is not None:
        raise ProviderUnavailableError(
            f"The provider '{provider.display_name}' is not available: {unavailable_reason}"
        )
    return provider
