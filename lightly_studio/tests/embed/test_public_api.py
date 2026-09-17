from lightly_studio_serve.embedder import Capability, Embedder
from pytest_mock import MockerFixture

from lightly_studio.embed import embedder_registry, public_api
from lightly_studio.embed.embedder_registry import EmbedderRegistry


def test_register_default_embedder(mocker: MockerFixture) -> None:
    registry = mocker.MagicMock(spec=EmbedderRegistry)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    embedder = mocker.MagicMock(spec=Embedder)

    public_api.register_default_embedder(embedder=embedder)

    registry.register.assert_called_once_with(embedder=embedder, bootstrap_for=None)


def test_register_default_embedder__bootstrap_for(mocker: MockerFixture) -> None:
    registry = mocker.MagicMock(spec=EmbedderRegistry)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    embedder = mocker.MagicMock(spec=Embedder)
    bootstrap_for = {Capability.TEXT}

    public_api.register_default_embedder(embedder=embedder, bootstrap_for=bootstrap_for)

    registry.register.assert_called_once_with(embedder=embedder, bootstrap_for=bootstrap_for)
