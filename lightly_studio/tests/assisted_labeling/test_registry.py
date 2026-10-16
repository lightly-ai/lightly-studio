from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lightly_studio.assisted_labeling import provider_ids, registry
from lightly_studio.assisted_labeling.fake_provider import FakeProvider


@pytest.fixture(autouse=True)
def reset_instances(mocker: MockerFixture) -> None:
    mocker.patch.object(registry, "_instances", None)


def test_get_provider__lazy(mocker: MockerFixture) -> None:
    factory = mocker.Mock(side_effect=FakeProvider)
    mocker.patch.dict(registry._FACTORIES, {provider_ids.FAKE_PROVIDER_ID: factory})

    registry.get_provider_ids()
    factory.assert_not_called()

    first = registry.get_provider(provider_ids.FAKE_PROVIDER_ID)
    second = registry.get_provider(provider_ids.FAKE_PROVIDER_ID)

    factory.assert_called_once()
    assert first is second


def test_get_provider__unknown_id() -> None:
    with pytest.raises(ValueError, match="Available providers: fake"):
        registry.get_provider("unknown")


def test_list_providers__matches_ids() -> None:
    ids = [provider.provider_id for provider in registry.list_providers()]

    assert ids == registry.get_provider_ids()
