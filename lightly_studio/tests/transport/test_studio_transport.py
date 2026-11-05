from __future__ import annotations

from pytest_mock import MockerFixture

from lightly_studio.transport import studio_transport
from lightly_studio.transport.local.local_transport import LocalTransport


def test_get_transport__default_is_local() -> None:
    assert isinstance(studio_transport.get_transport(), LocalTransport)


def test_set_transport(mocker: MockerFixture) -> None:
    # Restore the active transport after the test.
    mocker.patch.object(studio_transport._active, "transport", LocalTransport())
    transport = LocalTransport()

    studio_transport.set_transport(transport=transport)

    assert studio_transport.get_transport() is transport
