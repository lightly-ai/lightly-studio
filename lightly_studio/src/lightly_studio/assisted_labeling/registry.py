"""Registry of the available assisted labeling providers."""

from __future__ import annotations

import threading
from collections.abc import Callable

from lightly_studio.assisted_labeling import provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.provider import AssistedLabelingProvider

_FACTORIES: dict[str, Callable[[], AssistedLabelingProvider]] = {
    provider_ids.FAKE_PROVIDER_ID: FakeProvider,
    provider_ids.FAL_SAM3_PROVIDER_ID: FalSam3Provider,
}

_lock = threading.Lock()
# Built on first use and kept, so that provider caches persist.
_instances: dict[str, AssistedLabelingProvider] | None = None


def get_provider(provider_id: str) -> AssistedLabelingProvider:
    """Returns the provider with the ID.

    Raises:
        ValueError: If no provider has the ID.
    """
    provider = _get_instances().get(provider_id)
    if provider is None:
        raise ValueError(
            f"Unknown assisted labeling provider '{provider_id}'. "
            f"Available providers: {', '.join(get_provider_ids())}."
        )
    return provider


def list_providers() -> list[AssistedLabelingProvider]:
    """Returns all providers."""
    return list(_get_instances().values())


def get_provider_ids() -> list[str]:
    """Returns the IDs of all providers without building them."""
    return list(_FACTORIES)


def _get_instances() -> dict[str, AssistedLabelingProvider]:
    global _instances  # noqa: PLW0603
    with _lock:
        if _instances is None:
            _instances = {provider_id: factory() for provider_id, factory in _FACTORIES.items()}
        return _instances
