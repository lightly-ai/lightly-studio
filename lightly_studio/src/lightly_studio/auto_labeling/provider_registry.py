"""Registry for auto-labeling providers."""

from __future__ import annotations

from lightly_studio.auto_labeling.base_provider import BaseAutoLabelingProvider


class ProviderRegistry:
    """Global registry for auto-labeling providers."""

    def __init__(self):
        self._providers: dict[str, BaseAutoLabelingProvider] = {}

    def register(self, provider: BaseAutoLabelingProvider) -> None:
        """Register a provider.

        Args:
            provider: Provider instance to register.
        """
        self._providers[provider.provider_id] = provider

    def get_by_id(self, provider_id: str) -> BaseAutoLabelingProvider | None:
        """Get provider by ID.

        Args:
            provider_id: ID of the provider to retrieve.

        Returns:
            Provider instance if found, None otherwise.
        """
        return self._providers.get(provider_id)

    def get_all_metadata(self) -> list[dict]:
        """Get metadata for all registered providers.

        Returns:
            List of dictionaries containing provider metadata.
        """
        return [
            {
                "provider_id": p.provider_id,
                "name": p.name,
                "description": p.description,
            }
            for p in self._providers.values()
        ]


# Global provider registry instance
provider_registry = ProviderRegistry()
