from __future__ import annotations

from lightly_studio.embed.remote.endpoint import RemoteEndpoint


class TestRemoteEndpoint:
    def test_repr__hides_api_key(self) -> None:
        endpoint = RemoteEndpoint(url="http://embedder.test", api_key="secret-token")

        assert "secret-token" not in repr(endpoint)
