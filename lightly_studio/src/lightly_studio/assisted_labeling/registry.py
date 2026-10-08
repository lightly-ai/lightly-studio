"""Registry of the available assisted labeling providers."""

from __future__ import annotations

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.provider import AssistedLabelingProvider

DEFAULT_PROVIDER_ID = "fal_sam3"

# The providers are singletons, so that caches like uploaded image URLs persist.
_PROVIDERS: dict[str, AssistedLabelingProvider] = {
    provider.provider_id: provider for provider in (FalSam3Provider(), FakeProvider())
}


def get_provider(provider_id: str) -> AssistedLabelingProvider:
    """Returns the provider with the ID.

    Raises:
        ValueError: If no provider has the ID.
    """
    provider = _PROVIDERS.get(provider_id)
    if provider is None:
        raise ValueError(
            f"Unknown assisted labeling provider '{provider_id}'. "
            f"Available providers: {', '.join(_PROVIDERS)}."
        )
    return provider


def list_providers() -> list[AssistedLabelingProvider]:
    """Returns all providers."""
    return list(_PROVIDERS.values())
