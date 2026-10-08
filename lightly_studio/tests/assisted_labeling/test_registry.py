from __future__ import annotations

import pytest

from lightly_studio.assisted_labeling import registry
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.fal_sam3_provider import FalSam3Provider
from lightly_studio.assisted_labeling.openai_astra_provider import OpenAIAstraProvider


def test_get_provider() -> None:
    assert isinstance(registry.get_provider(provider_id="fal_sam3"), FalSam3Provider)
    assert isinstance(registry.get_provider(provider_id="fal_sam3_1"), FalSam3Provider)
    assert isinstance(registry.get_provider(provider_id="openai_astra"), OpenAIAstraProvider)
    assert isinstance(registry.get_provider(provider_id="fake"), FakeProvider)


def test_get_provider__singleton() -> None:
    assert registry.get_provider(provider_id="fal_sam3") is registry.get_provider(
        provider_id="fal_sam3"
    )


def test_get_provider__unknown() -> None:
    with pytest.raises(ValueError, match="Unknown assisted labeling provider 'other'"):
        registry.get_provider(provider_id="other")


def test_list_providers() -> None:
    provider_ids = [provider.provider_id for provider in registry.list_providers()]
    assert provider_ids == ["fal_sam3", "fal_sam3_1", "openai_astra", "fake"]
    assert registry.DEFAULT_PROVIDER_ID in provider_ids
