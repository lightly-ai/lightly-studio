from __future__ import annotations

from pytest_mock import MockerFixture

from lightly_studio.transport import studio_transport
from lightly_studio.transport.local.local_transport import LocalTransport


def test_get_transport__default_is_local(mocker: MockerFixture) -> None:
    mocker.patch.object(studio_transport, "_transport", None)

    transport = studio_transport.get_transport()

    assert isinstance(transport, LocalTransport)
    assert studio_transport.get_transport() is transport


def test_set_transport(mocker: MockerFixture) -> None:
    mocker.patch.object(studio_transport, "_transport", None)
    transport = LocalTransport()

    studio_transport.set_transport(transport=transport)

    assert studio_transport.get_transport() is transport
