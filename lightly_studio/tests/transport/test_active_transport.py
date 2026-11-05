from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from lightly_studio.transport import active_transport
from lightly_studio.transport.local.local_transport import LocalTransport


@pytest.fixture(autouse=True)
def restore_active_transport(mocker: MockerFixture) -> None:
    mocker.patch.object(active_transport._active, "transport", None)


def test_get_transport__default_is_local() -> None:
    assert isinstance(active_transport.get_transport(), LocalTransport)


def test_get_transport__default_is_kept() -> None:
    assert active_transport.get_transport() is active_transport.get_transport()


def test_set_transport() -> None:
    transport = LocalTransport()

    active_transport.set_transport(transport=transport)

    assert active_transport.get_transport() is transport


def test_set_transport__none_sets_default() -> None:
    transport = LocalTransport()
    active_transport.set_transport(transport=transport)

    active_transport.set_transport(transport=None)

    active = active_transport.get_transport()
    assert isinstance(active, LocalTransport)
    assert active is not transport
